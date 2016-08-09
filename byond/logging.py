def debug(filename, line, path, message):
    '''
    Print a simple debugging message
    '''
    print('{0}:{1}: {2} - {3}'.format(filename, line, '/'.join(path), message))
