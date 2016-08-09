from . import Atom

class Proc(Atom):
    """
    No clue why this is a subtype of Atom
    """
    def __init__(self, path, arguments, filename='', line=0):
        # NOTE: Fix when obsoleting Py27
        super(Proc, self).__init__(self, path, filename, line)
        self.name = self.figureOutName(self.path)
        self.arguments = arguments
        self.code = []  # (indent, line)
        self.definition = False
        self.origpath = ''

    def figureOutName(self, path):
        name = path.split('(')[0]
        return name.split('/')[-1]

    def CountTabs(self, line):
        m = REGEX_TABS.match(line)
        if m is not None:
            return len(m.group('tabs'))
        return 0

    def AddCode(self, indentLevel, line):
        self.code.append( (indentLevel, line) )

    def ClearCode(self):
        self.code = []

    def AddBlankLine(self):
        if len(self.code) > 0 and self.code[-1][1] == '':
            return
        self.code += [(0, '')]

    def MapSerialize(self, flags=0):
        return None

    def InheritProperties(self):
        return
    def getMinimumIndent(self):
        # Find minimum indent level
        for i in range(len(self.code)):
            indent, _ = self.code[i]
            if indent == 0: continue
            return indent
        return 0

    def _DumpCode(self):
        args = self.path[self.path.index('('):]
        true_path = self.path[:self.path.index('(')].split('/')
        name = true_path[-1]
        true_path = true_path[:-1]
        if self.definition:
            true_path += ['proc']
        true_path += [name + args]
        o = '\n' + '/'.join(true_path) + '\n'
        min_indent = self.getMinimumIndent()
        # Should be 1, so find the difference.
        indent_delta = 1 - min_indent
        # o += '\t// true_path  = {0}\n'.format(repr(true_path))
        # o += '\t// name       = {0}\n'.format(name)
        # o += '\t// args       = {0}\n'.format(args)
        # o += '\t// definition = {0}\n'.format(self.definition)
        # o += '\t// path       = {0}\n'.format(self.path[:self.path.index('(')])
        # o += '\t// origpath   = {0}\n'.format(self.origpath)
        # o += '\t// min_indent = {0}\n'.format(min_indent)
        # o += '\t// indent_delta = {0}\n'.format(indent_delta)
        for i in range(len(self.code)):
            indent, code = self.code[i]
            indent = max(1, indent + indent_delta)
            if code == '' and i == len(self.code) - 1:
                continue
            if code.strip() == '':
                o += '\n'
            else:
                o += (indent * '\t') + code.strip() + '\n'
        return o
