class BYONDValue(object):
    """
    The parent type of all BYOND vars
    """
    def __init__(self, string, filename='', line=0, typepath='/', **kwargs):
        #: The actual value.
        self.value = string

        #: Filename this was found in
        self.filename = filename

        #: Line of the originating file.
        self.line = line

        #: Typepath of the value.
        self.type = typepath

        #: Has this value been inherited?
        self.inherited = kwargs.get('inherited', False)

        #: Is this a declaration? (/var)
        self.declaration = kwargs.get('declaration', False)

        #: Anything special? (global, const, etc.)
        self.special = kwargs.get('special', None)

        #: If a list, what's the size?
        self.size = kwargs.get('size', None)

    def copy(self):
        '''Make a clone of this without dangling references.'''
        return self.__class__(self.value, self.filename, self.line, self.type, declaration=self.declaration, inherited=self.inherited, special=self.special)

    def __str__(self):
        if self.value is None:
            return 'null'
        return '{0}'.format(self.value)

    def __repr__(self):
        return '<{} value="{}" filename="{}" line={}>'.format(self.__class__.__name__, self.value, self.filename, self.line)

    def DumpCode(self, name):
        '''
        Try to dump valid BYOND code for this variable.

        .. :param name: The name of this variable.
        '''
        decl = []
        if self.declaration:
            decl += ['var']
        if self.type != '/' and self.declaration:
            decl += self.type.split('/')[1:]
        decl += [name]
        constructed = '/'.join(decl)
        if self.value is not None:
            constructed += ' = {0}'.format(str(self))
        return constructed
