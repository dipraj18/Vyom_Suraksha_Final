class SecretGuard:
    def __init__(self):
        self.allowed = True

    def update_permission(self, system_state):
        if system_state.value == "NORMAL":
            self.allowed = True
        else:
            self.allowed = False

    def can_access_secret(self):
        return self.allowed