class DomainError(Exception):
    """A business rule rejected the requested operation."""


class PermissionDenied(DomainError):
    pass


class ValidationError(DomainError):
    pass


class DuplicateStudent(DomainError):
    def __init__(self, student_id: int, active: bool) -> None:
        self.student_id = student_id
        self.active = active
        super().__init__("Ya existe un alumno con ese DNI.")


class PriceNotConfigured(DomainError):
    pass


class DuplicatePayment(DomainError):
    pass
