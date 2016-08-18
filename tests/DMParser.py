import unittest

class DMParserTests(unittest.TestCase):
    def setUp(self):
        from byond.script.dmscript import DreamSyntax
        self.syntax = DreamSyntax()

    def testAbsPath(self):
        test_string = """
/obj/item/weapon/sword
        """
        test_string = test_string.strip()

        result = self.syntax.path.parseString(test_string)

        print(repr(result))

    def testVarDeclaration1(self):
        test_string = """
var/obj/item/thing
        """.strip()
        result = self.syntax.vardecl.parseString(test_string)

        print(repr(result))

    def testVarDeclaration2(self):
        test_string = """
var/mob/living/carbon/human/H
        """.strip()

        result = self.syntax.vardecl.parseString(test_string)

        print(repr(result))


    def testVarDeclaration3(self):
        # nonsense for now
        test_string = """
var/mob/living/carbon/human/H = 5
        """.strip()

        result = self.syntax.vardecl.parseString(test_string)

        print(repr(result))

# First comes absolute declaration support
#     def testBlockVarDeclaration(self):
#         test_string = """
# var
#     time
#     age
#     speed
#         """.strip()
#         indentStack = [1]
#         import pyparsing as pyp
#         ident = pyp.pyparsing_common.identifier
#         varname = ident.setResultsName("varname")
#         stmt = pyp.Forward()
#         varblock_body = pyp.indentedBlock(stmt, indentStack)
#         stmt << (varname)
#
#         varblock_start = pyp.Keyword("var")
#         var_block = pyp.Group(varblock_start + varblock_body)
#
#         result = var_block.parseString(test_string)
#
#         result.pprint()
#
#         raise Exception

    def testAtomVarDeclaration(self):
        test_string = """
/obj/item/weapon/tool/crowbar
    var/color = "#00FF00"
    name = "Crowbar"
    var/greytideyness
        """.strip()

        self.syntax.reset()
        self.syntax.ParseString(test_string)
