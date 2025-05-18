# 초기에는 mock ID 반환
def get_current_user_id():
    """
    현재 로그인된 사용자의 ID를 반환합니다.
    MVP 단계에서는 고정된 테스트 사용자 ID를 반환합니다.
    """
    return "test_user"

def is_user_logged_in():
    """
    사용자 로그인 상태를 확인합니다.
    MVP 단계에서는 항상 로그인된 것으로 간주합니다.
    """
    return True

# Firebase 연동 시 실제 인증 로직으로 대체될 부분
# import firebase_admin
# from firebase_admin import credentials, auth

# def init_firebase():
#     # Firebase Admin SDK 초기화 (config.py 등에서 설정 가져오기)
#     # cred_path = "path/to/your/serviceAccountKey.json"
#     # if not firebase_admin._apps:
#     #     cred = credentials.Certificate(cred_path)
#     #     firebase_admin.initialize_app(cred)
#     pass

# def verify_firebase_token(id_token):
#     # id_token을 검증하고 사용자 정보를 반환
#     # try:
#     #     decoded_token = auth.verify_id_token(id_token)
#     #     uid = decoded_token['uid']
#     #     return uid
#     # except Exception as e:
#     #     print(f"Firebase token verification failed: {e}")
#     #     return None
#     pass