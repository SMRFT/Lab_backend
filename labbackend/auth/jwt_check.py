import jwt
import os
import base64
import time
import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from . import permissions_map as permissions

PUBLIC_KEY_NAME =  'GLOBAL_PUBLIC_KEY'
ISSUER_KEY =  'iss'
ISSUER_VALUE =  'https://lab.shinova.in/'
ISSUED_AT_KEY = "iat"
EXPIRES_AT_KEY = "exp"
AUD_KEY = "aud"

ALLOWED_DATA_KEY = 'allowed-data'
ALLOWED_ACTIONS_KEY = 'allowed-actions'

AUTHZ_MODEL = 'IMPLIED'
AUTHZ_MODEL_IMPLIED = 'IMPLIED'

_pubk_B64 = os.environ[PUBLIC_KEY_NAME]
if not _pubk_B64:
   raise ValueError(f'Private key ({PUBLIC_KEY_NAME}) not set')

_pubk = base64.b64decode(_pubk_B64) 

PUBLIC_KEY = serialization.load_pem_public_key(
   _pubk, backend=default_backend())

def __checkJwt(accessToken:str):

   ct = round(time.time())
   unverified = jwt.decode(accessToken, options={"verify_signature": False})

   if unverified[ISSUER_KEY] != ISSUER_VALUE :
      raise ValueError(f'Invalid access token [Token not from trusted source]')
   elif unverified[ISSUED_AT_KEY] > ct :
      raise ValueError(f'Invalid access token [Token is not yet valid]')
   elif unverified[EXPIRES_AT_KEY] < ct :
      raise ValueError(f'Invalid access token [Token expired]')

   tokenAud = unverified[AUD_KEY]

   verified = jwt.decode(accessToken, key=_pubk, algorithms="RS256", audience=tokenAud)
   return verified

def checkAccess(accessToken:str, 
                data:str, 
                page:str, 
                action:str) -> dict:

   vJson = __checkJwt(accessToken)

   # Data validation
   if data not in vJson[ALLOWED_DATA_KEY]:
      raise ValueError(f'Access denied [Not entitled to access requested data {data}]', data)

   # Permission validation
   pageId = permissions.PAGE_MAPPING[page]
   if not pageId:
      raise ValueError(f'Access denied [Invalid page]')

   if pageId in permissions.PAGE_ACTION_MAPPING and action in permissions.PAGE_ACTION_MAPPING[pageId]:
      actionId = permissions.PAGE_ACTION_MAPPING[pageId][action]
   else:
      actionId = permissions.GEN_ACTION_MAPPING[action]

   if not actionId:
      raise ValueError(f'Access denied [Invalid action]')

   permissionId = pageId + '-' + actionId    

   if permissionId not in vJson[ALLOWED_ACTIONS_KEY]:
      if AUTHZ_MODEL == AUTHZ_MODEL_IMPLIED:
         for k in vJson[ALLOWED_ACTIONS_KEY]:
            if k.startswith(permissionId):
               break
         else:
               raise ValueError(f'Access denied [Not allowed to perform {action} on {page}]',action, page)
      else:      
         raise ValueError(f'Access denied [Not allowed to perform {action} on {page}]',action, page)

   # Allowed access
   return vJson
