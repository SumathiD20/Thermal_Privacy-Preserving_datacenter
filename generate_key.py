from cryptography.fernet import Fernet
open('secret.key','wb').write(Fernet.generate_key())
print("secret.key created")
