class TrieNode:
    def __init__(self):
        self.children = [None] * 26
        self.is_end = False

class Trie:
    def __init__(self):
        self.root = TrieNode()
    
    def insert(self, word):
        node = self.root
        for char in word:
            index = ord(char) - ord('A')
            if not node.children[index]:
                node.children[index] = TrieNode()
            node = node.children[index]
        node.is_end = True
    
    def search(self, word):
        node = self.root
        for char in word:
            index = ord(char) - ord('A')
            if not node.children[index]:
                return False
            node = node.children[index]
        return node.is_end