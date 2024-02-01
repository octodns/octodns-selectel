from octodns.provider import ProviderException


class SelectelException(ProviderException):
    pass


class ApiException(SelectelException):
    pass
