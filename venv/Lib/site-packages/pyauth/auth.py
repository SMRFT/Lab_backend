from rest_framework import permissions
from .jwt_check import isSecurityDisabled, checkAccess, checkAccessForData, checkAccessForPageAction
from .jwt_check import AUD_KEY

AUTH_USERID_KEY =  'auth-user-id'
AUTH_BRANCH_CODE_KEY =  'auth-branch-code'

class HasRoleAndDataPermission(permissions.BasePermission):
    def has_permission(self, request, view) -> bool:
        if isSecurityDisabled():
            print(f'''
                  WARNING: Security disabled in this environment 
                  HasRoleAndDataPermission check skipped
                  auth-user-id & auth-branch-code values not set
                ''')
            return True
        try:
            token = request.headers["Authorization"]
            branch_code = request.headers["Branch-Code"]
            page_path = request.get_full_path()
            http_method = request.method
            vjson = checkAccess(token, branch_code, page_path, http_method)
            request.data[AUTH_USERID_KEY] = vjson[AUD_KEY]
            request.data[AUTH_BRANCH_CODE_KEY] = branch_code
            print(f'HasRoleAndDataPermission: Access allowed\n')
            return True
        except ValueError as e:
            print(f'HasRoleAndDataPermission: Access not allowed. Reason: {e}\n')
            return False
        except:
            print(f'HasRoleAndDataPermission: Error occured in access validation')
            return False

class HasDataPermission(permissions.BasePermission):
    def has_permission(self, request, view) -> bool:
        if isSecurityDisabled():
            print(f'''
                  WARNING: Security disabled in this environment 
                  HasDataPermission check skipped
                  auth-user-id & auth-branch-code values not set
                ''')
            return True
        try:
            token = request.headers["Authorization"]
            branch_code = request.headers["Branch-Code"]
            vjson = checkAccessForData(token, branch_code)
            request.headers[AUTH_USERID_KEY] = vjson[AUD_KEY]
            request.headers[AUTH_BRANCH_CODE_KEY] = branch_code
            print(f'HasDataPermission: Access allowed\n')
            return True
        except ValueError as e:
            print(f'HasDataPermission: Access not allowed. Reason: {e}\n')
            return False
        except:
            print(f'HasDataPermission: Error occured in access validation')
            return False

class HasRolePermission(permissions.BasePermission):
    def has_permission(self, request, view):
        if isSecurityDisabled():
            print(f'''
                  WARNING: Security disabled in this environment 
                  HasRolePermission check skipped
                  auth-user-id value not set
                ''')
            return True
        try:
            token = request.headers["Authorization"]
            page_path = request.get_full_path()
            http_method = request.method
            vjson = checkAccessForPageAction(token, page_path, http_method)
            request.headers[AUTH_USERID_KEY] = vjson[AUD_KEY]
            request.headers[AUTH_BRANCH_CODE_KEY] = ""
            print(f'HasRolePermission: Access allowed\n')
            return True
        except ValueError as e:
            print(f'HasRolePermission: Access not allowed. Reason: {e}\n')
            return False
        except:
            print(f'HasRolePermission: Error occured in access validation')
            return False


