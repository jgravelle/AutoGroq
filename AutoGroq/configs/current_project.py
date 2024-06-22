
class Current_Project:
    def __init__(self):
        self.deliverables = []
        self.re_engineered_prompt = ""

    def add_deliverable(self, deliverable):
        self.deliverables.append({"text": deliverable, "done": False})


    def mark_deliverable_done(self, index):
        if 0 <= index < len(self.deliverables):
            self.deliverables[index]["done"] = True


    def mark_deliverable_undone(self, index):
        if 0 <= index < len(self.deliverables):
            self.deliverables[index]["done"] = False


    def set_re_engineered_prompt(self, prompt):
        self.re_engineered_prompt = prompt
