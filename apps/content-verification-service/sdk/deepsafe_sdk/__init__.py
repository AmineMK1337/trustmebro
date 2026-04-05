__all__ = [
    "PredictionResult",
    "ModelManifest",
    "load_manifest",
    "ensure_weights",
    "DeepSafeModel",
    "ImageModel",
    "VideoModel",
    "AudioModel",
    "create_app",
]


def __getattr__(name):
    if name == "PredictionResult":
        from deepsafe_sdk.types import PredictionResult

        return PredictionResult
    if name in {"ModelManifest", "load_manifest"}:
        from deepsafe_sdk.manifest import ModelManifest, load_manifest

        return {"ModelManifest": ModelManifest, "load_manifest": load_manifest}[name]
    if name == "ensure_weights":
        from deepsafe_sdk.weights import ensure_weights

        return ensure_weights
    if name == "DeepSafeModel":
        from deepsafe_sdk.base import DeepSafeModel

        return DeepSafeModel
    if name == "ImageModel":
        from deepsafe_sdk.image import ImageModel

        return ImageModel
    if name == "VideoModel":
        from deepsafe_sdk.video import VideoModel

        return VideoModel
    if name == "AudioModel":
        from deepsafe_sdk.audio import AudioModel

        return AudioModel
    if name == "create_app":
        from deepsafe_sdk.server import create_app

        return create_app
    raise AttributeError(f"module 'deepsafe_sdk' has no attribute '{name}'")
