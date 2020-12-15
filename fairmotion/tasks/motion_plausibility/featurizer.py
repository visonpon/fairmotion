import numpy as np

from fairmotion.ops import conversions
from fairmotion.utils import constants, utils


class Featurizer:
    def __init__(self, mean=None, std=None):
        self.mean = mean
        self.std = std

    def normalize(self, data):
        if self.mean is not None and self.std is not None:
            return (data - self.mean)/(self.std + constants.EPSILON)
        else:
            return data

    def featurize(self, prev_poses, pose):
        raise NotImplementedError


class RotationFeaturizer(Featurizer):
    def __init__(self, rep="aa", mean=None, std=None):
        assert rep in ["aa", "rotmat", "quat"]
        self.rep = rep
        super().__init__(mean, std)

    def featurize(self, prev_poses, pose):
        prev_data = np.array(
            [self.featurize_pose(prev_pose) for prev_pose in prev_poses]
        )
        cur_data = self.featurize_pose(pose)
        return self.normalize(prev_data), self.normalize(cur_data)

    def featurize_all(self, prev_and_current_poses):
        return self.normalize(
            np.array([
                self.featurize_pose(pose) for pose in prev_and_current_poses
            ])
        )

    def featurize_pose(self, pose):
        data = pose.rotations()
        convert_fn = conversions.convert_fn_from_R(self.rep)
        data = convert_fn(data)
        data = utils.flatten_angles(data, self.rep)
        return data


class FacingPositionFeaturizer(Featurizer):
    def featurize(self, prev_poses, pose):
        facing_r, facing_p = conversions.T2Rp(pose.get_facing_transform())
        prev_data = np.array([
            np.dot(
                (prev_pose.positions(local=False) - facing_p),
                facing_r,
            )
            for prev_pose in prev_poses
        ]).reshape(len(prev_poses), -1)
        cur_data = np.dot(
            (pose.positions(local=False) - facing_p),
            facing_r,
        ).flatten()
        return self.normalize(prev_data), self.normalize(cur_data)

    def featurize_all(self, prev_and_current_poses):
        prev_data, cur_data = self.featurize(
            prev_and_current_poses[:-1],
            prev_and_current_poses[-1],
        )
        return np.append(prev_data, np.expand_dims(cur_data, axis=0), axis=0)


def get_featurizer(feature_type, rep="aa"):
    if feature_type == "facing":
        featurizer = FacingPositionFeaturizer()
    else:
        featurizer = RotationFeaturizer(rep=rep)
    return featurizer