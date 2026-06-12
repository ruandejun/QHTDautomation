"""
captcha2upload.py - Stub module for captcha solving service integration.
Original module used a proprietary captcha uploading API.
This stub prevents ImportError while the real implementation is being restored.
"""


class Captcha2Upload:
    """Stub for captcha upload service."""
    
    def __init__(self, api_key=''):
        self.api_key = api_key
    
    def solve_image(self, image_path):
        """Solve image captcha. Returns solution string or None."""
        raise NotImplementedError(
            "captcha2upload is not implemented. "
            "Please configure a captcha solving service (e.g. 2captcha, anticaptcha)."
        )
    
    def solve_recaptcha(self, site_key, page_url):
        """Solve reCAPTCHA v2. Returns token or None."""
        raise NotImplementedError(
            "captcha2upload is not implemented. "
            "Please configure a captcha solving service."
        )
    
    def get_balance(self):
        """Get account balance."""
        return 0.0


# Module-level convenience instance (used by legacy code)
def solve_image(api_key, image_path):
    """Solve an image captcha using configured API key."""
    solver = Captcha2Upload(api_key)
    return solver.solve_image(image_path)
