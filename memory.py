class Memory:
    def __init__(self):
        self.data = {}

    def get(self, user):
        return self.data.get(user, [])

    def update(self, user, message):
        if user not in self.data:
            self.data[user] = []
        self.data[user].append(message)

    def clear(self, user):
        if user in self.data:
            self.data[user] = []
