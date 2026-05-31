from typing import Any, Dict, Optional

class AppException(Exception):
    """
    Uygulama genelindeki tüm özel hataların türediği temel Exception sınıfı.
    {"error": {"code": self.code, "message": self.message}}
    """
    def __init__(self, code: str, message: str, status_code: int = 400, details: Optional[Dict[str, Any]] = None):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(self.message)

class AuthException(AppException):
    def __init__(self, message: str, status_code: int = 401, details: Optional[Dict[str, Any]] = None):
        super().__init__(code="AUTH_ERROR", message=message, status_code=status_code, details=details)

class NotFoundException(AppException):
    def __init__(self, resource: str, message: str = "Kaynak bulunamadı"):
        super().__init__(code="NOT_FOUND", message=f"{resource}: {message}", status_code=404)

class ValidationException(AppException):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(code="VALIDATION_ERROR", message=message, status_code=422, details=details)

class BusinessLogicException(AppException):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(code="BUSINESS_LOGIC_ERROR", message=message, status_code=400, details=details)

class PermissionException(AppException):
    def __init__(self, message: str = "Bu işlem için yetkiniz yok"):
        super().__init__(code="FORBIDDEN", message=message, status_code=403)
