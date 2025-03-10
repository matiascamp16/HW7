class Tree:
    def __init__(self, name, value):
        self.name = name
        self.value = value
        self.children = []
    
    def add_child(self, child):
        self.children.append(child)
    
    def prune(self):
        for child in self.children[:]:
            child.prune()
        self.children = [c for c in self.children if c.children]
    
    def allnodes(self):
        nodes = [self]
        for child in self.children:
            nodes.extend(child.allnodes())
        return nodes
def dict_filter(func, d):
    return {k: v for k, v in d.items() if func(k, v)}

class KVTree:
    def __init__(self, key, value):
        self.key = key
        self.value = value
        self.children = []
    
    def add_child(self, child):
        self.children.append(child)

def treemap(func, tree):
    new_key, new_value = func(tree.key, tree.value)
    tree.key = new_key
    tree.value = new_value
    for child in tree.children:
        treemap(func, child)
class DTree:
    def __init__(self, variable, threshold, lessequal, greater, outcome):
        if (outcome is None and (variable is None or threshold is None or lessequal is None or greater is None)) or \
           (outcome is not None and (variable is not None or threshold is not None or lessequal is not None or greater is not None)):
            raise ValueError("Invalid parameters")
        self.variable = variable
        self.threshold = threshold
        self.lessequal = lessequal
        self.greater = greater
        self.outcome = outcome
    
    def tuple_atleast(self):
        variables = set()
        def helper(node):
            if node.outcome is None:
                variables.add(node.variable)
                helper(node.lessequal)
                helper(node.greater)
        helper(self)
        return max(variables) + 1 if variables else 0
    
    def find_outcome(self, observations):
        current = self
        while current.outcome is None:
            value = observations[current.variable]
            current = current.lessequal if value <= current.threshold else current.greater
        return current.outcome
    
    def no_repeats(self):
        def helper(node, seen):
            if node.outcome is not None:
                return True
            if node.variable in seen:
                return False
            return helper(node.lessequal, seen | {node.variable}) and helper(node.greater, seen | {node.variable})
        return helper(self, set())