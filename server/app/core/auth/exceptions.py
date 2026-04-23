"""Excepciones personalizadas para autenticación."""


class AuthenticationError(Exception):
    def __init__(self, message: str = "Authentication failed"):
        self.message = message
        super().__init__(self.message)


class AuthorizationError(Exception):
    def __init__(self, message: str = "Insufficient permissions"):
        self.message = message
        super().__init__(self.message)
