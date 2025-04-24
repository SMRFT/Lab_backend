from rest_framework import permissions
from .jwt_check import checkAccess

class HasRoleAndDataPermission(permissions.BasePermission):
    """
    Global permission check for blocked IPs.
    """

    def has_permission(self, request, view):
        try:
            token = request.headers["Authorization"]
            branch_code = request.headers["Branch-Code"]
            page_path = request.get_full_path()
            http_method = request.method
            checkAccess(token, branch_code, page_path, http_method)
            print(f'Access allowed\n')
            return True
        except ValueError as e:
            print(f'Access not allowed. Reason: {e}\n')
            return False
        except:
            print(f'Error occured in access validation')
            return False
