
class Current_Project:
    def __init__(self):
        self.deliverables = []
        self.re_engineered_prompt = ""
        self.implementation_phases = ["Planning", "Development", "Testing", "Deployment"]
        self.current_phase = "Planning"


    def add_deliverable(self, deliverable):
        self.deliverables.append({
            "text": deliverable, 
            "done": False,
            "phase": {phase: False for phase in self.implementation_phases}
        })


    def get_next_unchecked_deliverable(self):
        for index, deliverable in enumerate(self.deliverables):
            if not deliverable["done"]:
                return index, deliverable["text"]
        return None, None
    

    def get_next_uncompleted_phase(self, index):
        if 0 <= index < len(self.deliverables):
            for phase in self.implementation_phases:
                if not self.deliverables[index]["phase"][phase]:
                    return phase
        return None    


    def is_deliverable_complete(self, index):
        if 0 <= index < len(self.deliverables):
            return all(self.deliverables[index]["phase"].values())
        return False


    def mark_deliverable_phase_done(self, index, phase):
        if 0 <= index < len(self.deliverables):
            self.deliverables[index]["phase"][phase] = True
            if self.is_deliverable_complete(index):
                self.deliverables[index]["done"] = True
                

    def mark_deliverable_undone(self, index):
        if 0 <= index < len(self.deliverables):
            self.deliverables[index]["done"] = False


    def move_to_next_phase(self):
        current_index = self.implementation_phases.index(self.current_phase)
        if current_index < len(self.implementation_phases) - 1:
            self.current_phase = self.implementation_phases[current_index + 1]            


    def set_re_engineered_prompt(self, prompt):
        self.re_engineered_prompt = prompt
