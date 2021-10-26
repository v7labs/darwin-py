class Team:
    def __init__(self, id: int, name: str, slug: str, selected: bool = False):
        self.id: int = id
        self.name: str = name
        self.slug: str = slug
        self.selected: bool = selected
