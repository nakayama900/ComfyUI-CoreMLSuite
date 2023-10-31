import os

import torch

from comfy.model_management import get_torch_device
from coreml_suite.lcm.lcm_pipeline import LatentConsistencyModelPipeline
from coreml_suite.lcm.lcm_scheduler import LCMScheduler
from coreml_suite.models import get_model_config, CoreMLModelWrapperLCM


class CoreMLSamplerLCM_Simple:
    def __init__(self):
        self.scheduler = LCMScheduler.from_pretrained(
            os.path.join(os.path.dirname(__file__), "scheduler_config.json")
        )
        self.pipe = None

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "coreml_model": ("COREML_UNET",),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xFFFFFFFFFFFFFFFF}),
                "steps": ("INT", {"default": 4, "min": 1, "max": 10000}),
                "cfg": (
                    "FLOAT",
                    {
                        "default": 8.0,
                        "min": 0.0,
                        "max": 100.0,
                        "step": 0.5,
                        "round": 0.01,
                    },
                ),
                "num_images": ("INT", {"default": 1, "min": 1, "max": 64}),
                "positive_prompt": ("STRING", {"multiline": True}),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "sample"
    CATEGORY = "sampling"

    def sample(
            self,
            coreml_model,
            seed,
            steps,
            cfg,
            positive_prompt,
            num_images,
    ):
        height = coreml_model.expected_inputs["sample"]["shape"][2] * 8
        width = coreml_model.expected_inputs["sample"]["shape"][3] * 8

        model_config = get_model_config()
        wrapped_model = CoreMLModelWrapperLCM(model_config, coreml_model)

        if self.pipe is None:
            self.pipe = LatentConsistencyModelPipeline.from_pretrained(
                pretrained_model_name_or_path="SimianLuo/LCM_Dreamshaper_v7",
                scheduler=self.scheduler,
                safety_checker=None,
            )

            self.pipe.to(torch_device=get_torch_device(), torch_dtype=torch.float16)

        coreml_unet = wrapped_model
        coreml_unet.config = self.pipe.unet.config

        self.pipe.unet = coreml_unet

        torch.manual_seed(seed)

        result = self.pipe(
            prompt=positive_prompt,
            width=width,
            height=height,
            guidance_scale=cfg,
            num_inference_steps=steps,
            num_images_per_prompt=num_images,
            lcm_origin_steps=50,
            output_type="np",
        ).images

        images_tensor = torch.from_numpy(result)

        return (images_tensor,)
