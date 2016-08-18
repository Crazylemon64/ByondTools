"""
Copyright (c)2015 Rob "N3X15" Nelson

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
the Software, and to permit persons to whom the Software is furnished to do so,
subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

:author: Rob "N3X15" Nelson <nexisentertainment@gmail.com>
"""
from __future__ import print_function
from byond.basetypes import BYONDFileRef, BYONDString, BYONDNumber#, BYONDList
import pyparsing as pyp
from pyparsing import pyparsing_common as pypc
import logging

# from .code_block import DMCodeBlock

class PPStackElement(object):
    """
    Not sure what this does.

    Guesses:
        PyParsing Stack Element...?
        Preprocessor Stack element...?

    args:
        blocking: ???
        ends: ???
        toggles: ???
    """
    def __init__(self, ends=[], toggles=[], blocking=False):
        self.blocking = blocking
        self.ends = ends
        self.toggles = toggles

    def isBlocking(self):
        return self.blocking

    def gotToken(self, name):
        if name in self.ends:
            return False  # Pop off stack
        if name in self.toggles:
            self.blocking = not self.blocking
        return True  # continue

class IfDefElement(PPStackElement):
    """
    Also not sure what this does, either.

    Guesses:
        Reads #ifdef statements, blocks on else and endif
    args:
        state: Something something blocking
    """
    def __init__(self, state):
        super(IfDefElement, self).__init__(ends=['endif'], toggles=['else'], blocking=state)

class DreamSyntax(object):
    """
    Parses DM code.
    """

    def __init__(self, list_only=False, simplify_lists=False):
        if list_only:
            self.syntax = self.buildListSyntax()
        else:
            self.syntax = self.buildSyntax()

        self.simplify_lists = simplify_lists

        #: Preprocessor defines.
        self.macros = {}

        #: Current #ifdef stack. (PPStackElement)
        self.ifstack = []

        self.atomContext = []
        self.log = logging.getLogger(__name__)

    def ParseString(self, filename, string):
        # try:
        return self.syntax.parseString(string)
        # except pyp.ParseException as err:
        #     self.log.critical(err.line)
        #     self.log.critical("-"*(err.column - 1) + "^")
        #     self.log.critical(err)

    def buildLiteralSyntax(self):
        """
        Initializes grammar for literal statements in BYOND
        """
        # Literals
        singlelineString = pyp.QuotedString('"', '\\').setResultsName('string').setParseAction(self.makeString)
        fileRef = pyp.QuotedString("'", '\\').setResultsName('fileRef').setParseAction(self.makeFileRef)
        multilineString = pyp.QuotedString(quoteChar='{"', endQuoteChar='"}', multiline=True).setResultsName('string').setParseAction(self.makeString)
        number = pyp.Regex(r'\d+(\.\d*)?([eE]\d+)?').setResultsName('number').setParseAction(self.makeNumber)

        self.literal << (singlelineString | fileRef | multilineString | number | self.dreamList)

    def buildPathSyntax(self):
        """
        Initializes grammar for reading type paths in BYOND
        """
        #  Paths
        # TODO: add support for checking which paths have already been declared yet,
        # and which haven't

        pathbit = pypc.identifier
        pathdivider = pyp.Suppress(self.SLASH)
        # Relpath goes all the way, grabs everything in the path
        self.relpath = pyp.Forward()
        self.relpath << (pathbit + pathdivider + self.relpath | pathbit)

        # Varpath leaves the last one behind, for use as the name of the var
        self.varpath = pyp.Forward()
        self.varpath << (pathbit + pathdivider + self.varpath | pyp.FollowedBy(pypc.identifier))

        self.abspath = pathdivider + self.relpath

        self.path = (self.abspath | self.relpath)
        # self.path.setParseAction(self.handlePath)
        self.pathslash = self.path + self.SLASH

    def buildDeclarationSyntax(self):
        # Two beasts to worry about
        #   Absolute pathing
        #   Relative pathing
        # The latter does not play as nice with parsing.
        self.path_identifier = pypc.identifier

        # Keywords
        self.VAR_GLOBAL = pyp.Keyword('global')
        self.VAR_CONST = pyp.Keyword('const')
        self.VAR = pyp.Keyword('var')

        arg_var_path = pyp.Group(self.varpath).setResultsName('path')
        var_prefix = pyp.Suppress(self.VAR + self.SLASH)

        # Var Declarations
        ##########################
        var_modifiers = pyp.ZeroOrMore((self.VAR_GLOBAL | self.VAR_CONST) + self.SLASH).setResultsName('modifiers')
        # Make this also accept proc results when in code mode
        var_assignment = pyp.Suppress(self.EQUAL) + self.literal.setResultsName('assignment')

        # Variables declared on global scope
        self.var_declare_statement = var_prefix + pyp.Optional(var_modifiers) + pyp.Optional(arg_var_path) + pypc.identifier.setResultsName('name') + pyp.Optional(var_assignment)

        # Variables declared inside a function's argument block
        """
/proc/beep(obj/item/stuff)
/proc/yeah(var/mob/living/L,var/woah)
        """
        self.var_argument = pyp.Optional(var_prefix) + pyp.Optional(arg_var_path) + pypc.identifier.setResultsName('name') + pyp.Optional(var_assignment)

        # Variables declared below the start of an atom block
        """
/atom/movable
    dir = 2
    var/luminance
    var/area_master
    var/speed = 8
    var/datum/reagents/R
        """

        self.vardecl = self.var_argument

        # Varblock stuff - relative pathing. TODO
        """
obj
    item
        var
            weight
            size
        """
        # varblock_stack = [1]

        # varblock_inner_ref = pypc.identifier.setResultsName('name') + pyp.Optional(var_assignment)
        # varblock_inner_decl = var_modifiers + pyp.Optional(self.abspath) + self.SLASH + varblock_inner_ref
        # varblock_element = varblock_inner_decl | varblock_inner_ref
        # varblock = self.VAR + pyp.indentedBlock(varblock_inner_decl, varblock_stack)
        # inline_vardecl = self.VAR + varblock_inner_decl
        # self.vardecl = varblock | inline_vardecl

    def buildCodeStatements(self):
        # Var declarations, proc calls, assignments, and conditionals
        #
        self.codeStmnt = pyp.Forward()


        # Global procs
        # Datum procs (methods)

        var_decl = self.var_argument
        # assignment =
        proc_args = pyp.Optional(var_decl + pyp.OneOrMore(pyp.Suppress(",") + var_decl))
        proc_call = pypc.identifier + pyp.Suppress('(') + proc_args + pyp.Suppress(')')

        # Block control statements
        self.ifStatement = pyp.Keyword('if')
        self.elseStatement = pyp.Keyword('else')
        self.forStatement = pyp.Keyword('for')
        # This one needs to NOT mess up on do/while
        self.whileStatement = pyp.Keyword('while')
        self.doStatement = pyp.Keyword('do')

        self.codeStmnt << (proc_call)


    def buildSyntax(self):
        """WIP."""
        # There are two modes for parsing DM syntax:
        #   Declaration mode, which is used for setting default values, attributes,
        #       and procs.
        #       Contains var declarations, default assignments, and proc declarations
        #   Code mode, which is used for the contents of procs - consists of code
        #       block statements, and is capable of containing control flow statements
        #       too. Consists of repeated code statements or var declarations
        dreamScript = pyp.Forward()
        # Other symbols
        self.SLASH = pyp.Literal('/')
        self.EQUAL = pyp.Literal('=')
        self.literal = pyp.Forward()
        self.indent_stack = [1]

        self.buildListSyntax()
        self.buildPathSyntax()
        self.buildLiteralSyntax()
        self.buildDeclarationSyntax()
        # self.buildCodeStatements()

        #############################
        # Grammar
        #############################

        # TODO: De-tangle this nasty knot of mungled indent stacks

        # Statements
        # - These occur only in procs
            # Proc calls
            # Assignments
            # Declarations

        #  Preprocessor stuff
        # ppStatement = pyp.Forward()
        #
        # ppDefine = pyp.Keyword('#define') + pypc.identifier.setResultsName('name') + pyp.restOfLine.setResultsName('value')
        # ppUndef = pyp.Keyword('#undef') + pypc.identifier.setResultsName('name')
        #
        # ppIfdef = (pyp.Keyword('#ifdef') + pypc.identifier.setResultsName('name'))
        # ppIfndef = (pyp.Keyword('#ifndef') + pypc.identifier.setResultsName('name'))
        # ppElse = (pyp.Keyword('#else') + pypc.identifier.setResultsName('name'))
        # ppEndif = pyp.Keyword('#endif')
        #
        # ppStatement = pyp.lineStart + (ppDefine | ppUndef | ppIfdef | ppIfndef | ppElse | ppEndif)

        # # Pre-processor parse actions
        # ppDefine.setParseAction(self.handlePPDefine)
        # ppUndef.setParseAction(self.handlePPUndef)
        # ppIfDef.setParseAction(self.handlePPIfdef)
        # ppIfndef.setParseAction(self.handlePPIfndef)
        # ppElse.setParseAction(self.handlePPElse)

        # Proc Declarations
        # PROC = pyp.Keyword('proc')
        # proc_args = '(' + pyp.delimitedList(self.var_argument | pypc.identifier.setResultsName('name')) + ')'
        # # TODO Make this not accept literally anything
        # proc_instructions = pyp.Empty()
        # procblock_proc = pypc.identifier.setResultsName('name') + proc_args + pyp.indentedBlock(proc_instructions, self.indent_stack)
        # procblock = PROC + pyp.indentedBlock(procblock_proc, self.indent_stack)
        # # TODO: Make this no longer a no-op
        # self.procdecl = pyp.Empty()

        # Atom blocks
        self.atomdecl = pyp.Forward()
        self.atomdecl << self.path + pyp.indentedBlock(self.vardecl | self.atomdecl | self.procdecl, [1])


        return dreamScript

    def buildListSyntax(self):
        """
        Grammar for list parsing.
        """
        self.dreamList = pyp.Forward()

        # Other symbols
        listStart = pyp.Suppress('list(')
        listEnd = pyp.Suppress(')')

        # Grammar
        listConstant = self.literal
        listElement = listConstant | (listConstant + '=' + listConstant)
        listElement = pyp.operatorPrecedence(listElement, [
                                ("=", 2, pyp.opAssoc.LEFT,),
                                ])
        listContents = pyp.delimitedList(listElement)
        # This *might* be a hack? I'm not sure - the group makes multiple empty top-level dicts
        # dreamList << pyp.Group(listStart + listContents + listEnd)
        self.dreamList << (listStart + listContents + listEnd)
        self.dreamList.setParseAction(self.makeList)

    def buildMapSyntax(self):
        """Subset of grammar for DMM files.

           "aai" = (/obj/structure/sign/securearea{desc = "A warning sign which reads 'HIGH VOLTAGE'"; icon_state = "shock"; name = "HIGH VOLTAGE"; pixel_y = -32},/turf/space,/area)
        """
        dreamList = pyp.Forward()

        # Literals
        singlelineString = pyp.QuotedString('"', '\\').setResultsName('string').setParseAction(self.makeListString)
        fileRef = pyp.QuotedString("'", '\\').setResultsName('fileRef').setParseAction(self.makeFileRef)
        multilineString = pyp.QuotedString(quoteChar='{"', endQuoteChar='"}', multiline=True).setResultsName('string').setParseAction(self.makeListString)
        number = pyp.Regex(r'\-?\d+(\.\d*)?([eE]\d+)?').setResultsName('number').setParseAction(self.makeListNumber)

        #  Paths
        self.buildPathSyntax()

        # Other symbols
        listStart = pyp.Suppress('list(')
        openParen = pyp.Suppress("(")
        closeParen = pyp.Suppress(')')

        # Grammar
        listConstant = singlelineString | fileRef | multilineString | number | dreamList | self.abspath
        listElement = listConstant | (listConstant + '=' + listConstant)
        listElement = pyp.operatorPrecedence(listElement, [
                                ("=", 2, pyp.opAssoc.LEFT,),
                                ])
        listContents = pyp.delimitedList(listElement)
        dreamList << pyp.Group(listStart + listContents + closeParen)
        dreamList.setParseAction(self.makeList)


        # DMM Atom definition
        atomDefProperty = pypc.identifier + "=" + listConstant
        atomDefProperty = pyp.operatorPrecedence(atomDefProperty, [
                                ("=", 2, pyp.opAssoc.LEFT,),
                                ])
        atomDefPropertyListContents = pyp.delimitedList(listElement, delim=';')
        atomDefProperties = pyp.Suppress("{") + atomDefPropertyListContents + pyp.Suppress("}")
        atomDef = self.abspath + pyp.Optional(atomDefProperties)

        # DMM Tile Definition
        tileDefListContents = pyp.delimitedList(atomDef)
        tileDefAtomList = openParen + tileDefListContents + closeParen
        tileDef = singlelineString + '=' + tileDefAtomList
        tileDef.setParseAction(self.makeTileDef)
        return tileDef

    def makeListString(self, s, l, t):
        return self.makeString(s, l, t, True)

    def makeString(self, s, l, toks, from_list=False):
        # print('makeString(%r)' % toks[0])
        if self.simplify_lists and from_list:
            return [toks[0]]
        return [BYONDString(toks[0])]

    def makeFileRef(self, s, l, toks):
        # print('makeFileRef(%r)' % toks[0])
        return [BYONDFileRef(toks[0])]

    # Not sure why this is a thing...?
    def makeListNumber(self, s, l, toks):
        # print('makeListNumber(%r)' % repr(toks))
        return self.makeNumber(s, l, toks, True)

    def makeNumber(self, s, l, toks, from_list=False):
        # print('makeNumber(%r)' % toks[0])
        if self.simplify_lists and from_list:
            return [float(toks[0])]
        return [BYONDNumber(float(toks[0]))]

    def makeList(self, toks):
        # We grab only the first element because the second is an empty dict(?)
        # print(toks.dump())
        print('makeList(%r)' % toks)
        print(type(toks))
        print(repr(toks))
        print(type(toks[0]))
        print(repr(toks[0]))
        # print(type(toks[0][0]))
        # print(repr(toks[0][0]))
        if not isinstance(toks[0], pyp.ParseResults):  # Non-associative(list)
            print("Making list")
            l = []
            for tok in toks:
                # print(repr(tok))
                l.append(tok)
            return l
        else:  # Associative(dictionary)
            print("Making dict")
            d = {}
            # Middle token is "=", so we skip it
            print("Length of toks: {}".format(len(toks)))
            for k, _, v in toks:

                if(isinstance(k, pyp.ParseResults)):
                    print("ParseResult in dictionary: {} -> {}".format(k, v))
                    continue
                print("{} = {}".format(k, v))
                print("{} -> {}".format(type(k), type(v)))
                d[k] = v
            return d

    def reset(self):
        self.indent_stack = [1]

def ParseDreamList(string):
    return DreamSyntax(list_only=True, simplify_lists=True).ParseString(string)
