# Generated from ListLang.g4 by ANTLR 4.13.2
from antlr4 import *
if "." in __name__:
    from .ListLangParser import ListLangParser
else:
    from ListLangParser import ListLangParser

# This class defines a complete listener for a parse tree produced by ListLangParser.
class ListLangListener(ParseTreeListener):

    # Enter a parse tree produced by ListLangParser#program.
    def enterProgram(self, ctx:ListLangParser.ProgramContext):
        pass

    # Exit a parse tree produced by ListLangParser#program.
    def exitProgram(self, ctx:ListLangParser.ProgramContext):
        pass


    # Enter a parse tree produced by ListLangParser#functionDecl.
    def enterFunctionDecl(self, ctx:ListLangParser.FunctionDeclContext):
        pass

    # Exit a parse tree produced by ListLangParser#functionDecl.
    def exitFunctionDecl(self, ctx:ListLangParser.FunctionDeclContext):
        pass


    # Enter a parse tree produced by ListLangParser#parameterList.
    def enterParameterList(self, ctx:ListLangParser.ParameterListContext):
        pass

    # Exit a parse tree produced by ListLangParser#parameterList.
    def exitParameterList(self, ctx:ListLangParser.ParameterListContext):
        pass


    # Enter a parse tree produced by ListLangParser#parameter.
    def enterParameter(self, ctx:ListLangParser.ParameterContext):
        pass

    # Exit a parse tree produced by ListLangParser#parameter.
    def exitParameter(self, ctx:ListLangParser.ParameterContext):
        pass


    # Enter a parse tree produced by ListLangParser#identifierList.
    def enterIdentifierList(self, ctx:ListLangParser.IdentifierListContext):
        pass

    # Exit a parse tree produced by ListLangParser#identifierList.
    def exitIdentifierList(self, ctx:ListLangParser.IdentifierListContext):
        pass


    # Enter a parse tree produced by ListLangParser#ExpressionRightAssignment.
    def enterExpressionRightAssignment(self, ctx:ListLangParser.ExpressionRightAssignmentContext):
        pass

    # Exit a parse tree produced by ListLangParser#ExpressionRightAssignment.
    def exitExpressionRightAssignment(self, ctx:ListLangParser.ExpressionRightAssignmentContext):
        pass


    # Enter a parse tree produced by ListLangParser#IdentifierLeftAssignment.
    def enterIdentifierLeftAssignment(self, ctx:ListLangParser.IdentifierLeftAssignmentContext):
        pass

    # Exit a parse tree produced by ListLangParser#IdentifierLeftAssignment.
    def exitIdentifierLeftAssignment(self, ctx:ListLangParser.IdentifierLeftAssignmentContext):
        pass


    # Enter a parse tree produced by ListLangParser#IdentifierAssignExpression.
    def enterIdentifierAssignExpression(self, ctx:ListLangParser.IdentifierAssignExpressionContext):
        pass

    # Exit a parse tree produced by ListLangParser#IdentifierAssignExpression.
    def exitIdentifierAssignExpression(self, ctx:ListLangParser.IdentifierAssignExpressionContext):
        pass


    # Enter a parse tree produced by ListLangParser#ListElementAssignment.
    def enterListElementAssignment(self, ctx:ListLangParser.ListElementAssignmentContext):
        pass

    # Exit a parse tree produced by ListLangParser#ListElementAssignment.
    def exitListElementAssignment(self, ctx:ListLangParser.ListElementAssignmentContext):
        pass


    # Enter a parse tree produced by ListLangParser#ListElementAssignExpression.
    def enterListElementAssignExpression(self, ctx:ListLangParser.ListElementAssignExpressionContext):
        pass

    # Exit a parse tree produced by ListLangParser#ListElementAssignExpression.
    def exitListElementAssignExpression(self, ctx:ListLangParser.ListElementAssignExpressionContext):
        pass


    # Enter a parse tree produced by ListLangParser#StructFieldAssignment.
    def enterStructFieldAssignment(self, ctx:ListLangParser.StructFieldAssignmentContext):
        pass

    # Exit a parse tree produced by ListLangParser#StructFieldAssignment.
    def exitStructFieldAssignment(self, ctx:ListLangParser.StructFieldAssignmentContext):
        pass


    # Enter a parse tree produced by ListLangParser#StructFieldAssignExpression.
    def enterStructFieldAssignExpression(self, ctx:ListLangParser.StructFieldAssignExpressionContext):
        pass

    # Exit a parse tree produced by ListLangParser#StructFieldAssignExpression.
    def exitStructFieldAssignExpression(self, ctx:ListLangParser.StructFieldAssignExpressionContext):
        pass


    # Enter a parse tree produced by ListLangParser#multiAssignment.
    def enterMultiAssignment(self, ctx:ListLangParser.MultiAssignmentContext):
        pass

    # Exit a parse tree produced by ListLangParser#multiAssignment.
    def exitMultiAssignment(self, ctx:ListLangParser.MultiAssignmentContext):
        pass


    # Enter a parse tree produced by ListLangParser#assignmentStatement.
    def enterAssignmentStatement(self, ctx:ListLangParser.AssignmentStatementContext):
        pass

    # Exit a parse tree produced by ListLangParser#assignmentStatement.
    def exitAssignmentStatement(self, ctx:ListLangParser.AssignmentStatementContext):
        pass


    # Enter a parse tree produced by ListLangParser#statement.
    def enterStatement(self, ctx:ListLangParser.StatementContext):
        pass

    # Exit a parse tree produced by ListLangParser#statement.
    def exitStatement(self, ctx:ListLangParser.StatementContext):
        pass


    # Enter a parse tree produced by ListLangParser#breakStatement.
    def enterBreakStatement(self, ctx:ListLangParser.BreakStatementContext):
        pass

    # Exit a parse tree produced by ListLangParser#breakStatement.
    def exitBreakStatement(self, ctx:ListLangParser.BreakStatementContext):
        pass


    # Enter a parse tree produced by ListLangParser#continueStatement.
    def enterContinueStatement(self, ctx:ListLangParser.ContinueStatementContext):
        pass

    # Exit a parse tree produced by ListLangParser#continueStatement.
    def exitContinueStatement(self, ctx:ListLangParser.ContinueStatementContext):
        pass


    # Enter a parse tree produced by ListLangParser#statementBlock.
    def enterStatementBlock(self, ctx:ListLangParser.StatementBlockContext):
        pass

    # Exit a parse tree produced by ListLangParser#statementBlock.
    def exitStatementBlock(self, ctx:ListLangParser.StatementBlockContext):
        pass


    # Enter a parse tree produced by ListLangParser#ifStatement.
    def enterIfStatement(self, ctx:ListLangParser.IfStatementContext):
        pass

    # Exit a parse tree produced by ListLangParser#ifStatement.
    def exitIfStatement(self, ctx:ListLangParser.IfStatementContext):
        pass


    # Enter a parse tree produced by ListLangParser#whileStatement.
    def enterWhileStatement(self, ctx:ListLangParser.WhileStatementContext):
        pass

    # Exit a parse tree produced by ListLangParser#whileStatement.
    def exitWhileStatement(self, ctx:ListLangParser.WhileStatementContext):
        pass


    # Enter a parse tree produced by ListLangParser#doUntilStatement.
    def enterDoUntilStatement(self, ctx:ListLangParser.DoUntilStatementContext):
        pass

    # Exit a parse tree produced by ListLangParser#doUntilStatement.
    def exitDoUntilStatement(self, ctx:ListLangParser.DoUntilStatementContext):
        pass


    # Enter a parse tree produced by ListLangParser#forStatement.
    def enterForStatement(self, ctx:ListLangParser.ForStatementContext):
        pass

    # Exit a parse tree produced by ListLangParser#forStatement.
    def exitForStatement(self, ctx:ListLangParser.ForStatementContext):
        pass


    # Enter a parse tree produced by ListLangParser#switchStatement.
    def enterSwitchStatement(self, ctx:ListLangParser.SwitchStatementContext):
        pass

    # Exit a parse tree produced by ListLangParser#switchStatement.
    def exitSwitchStatement(self, ctx:ListLangParser.SwitchStatementContext):
        pass


    # Enter a parse tree produced by ListLangParser#caseClause.
    def enterCaseClause(self, ctx:ListLangParser.CaseClauseContext):
        pass

    # Exit a parse tree produced by ListLangParser#caseClause.
    def exitCaseClause(self, ctx:ListLangParser.CaseClauseContext):
        pass


    # Enter a parse tree produced by ListLangParser#returnStatement.
    def enterReturnStatement(self, ctx:ListLangParser.ReturnStatementContext):
        pass

    # Exit a parse tree produced by ListLangParser#returnStatement.
    def exitReturnStatement(self, ctx:ListLangParser.ReturnStatementContext):
        pass


    # Enter a parse tree produced by ListLangParser#writeStatement.
    def enterWriteStatement(self, ctx:ListLangParser.WriteStatementContext):
        pass

    # Exit a parse tree produced by ListLangParser#writeStatement.
    def exitWriteStatement(self, ctx:ListLangParser.WriteStatementContext):
        pass


    # Enter a parse tree produced by ListLangParser#argument.
    def enterArgument(self, ctx:ListLangParser.ArgumentContext):
        pass

    # Exit a parse tree produced by ListLangParser#argument.
    def exitArgument(self, ctx:ListLangParser.ArgumentContext):
        pass


    # Enter a parse tree produced by ListLangParser#argumentList.
    def enterArgumentList(self, ctx:ListLangParser.ArgumentListContext):
        pass

    # Exit a parse tree produced by ListLangParser#argumentList.
    def exitArgumentList(self, ctx:ListLangParser.ArgumentListContext):
        pass


    # Enter a parse tree produced by ListLangParser#functionCall.
    def enterFunctionCall(self, ctx:ListLangParser.FunctionCallContext):
        pass

    # Exit a parse tree produced by ListLangParser#functionCall.
    def exitFunctionCall(self, ctx:ListLangParser.FunctionCallContext):
        pass


    # Enter a parse tree produced by ListLangParser#expressionList.
    def enterExpressionList(self, ctx:ListLangParser.ExpressionListContext):
        pass

    # Exit a parse tree produced by ListLangParser#expressionList.
    def exitExpressionList(self, ctx:ListLangParser.ExpressionListContext):
        pass


    # Enter a parse tree produced by ListLangParser#MultiplyExpr.
    def enterMultiplyExpr(self, ctx:ListLangParser.MultiplyExprContext):
        pass

    # Exit a parse tree produced by ListLangParser#MultiplyExpr.
    def exitMultiplyExpr(self, ctx:ListLangParser.MultiplyExprContext):
        pass


    # Enter a parse tree produced by ListLangParser#ComparisonExpr.
    def enterComparisonExpr(self, ctx:ListLangParser.ComparisonExprContext):
        pass

    # Exit a parse tree produced by ListLangParser#ComparisonExpr.
    def exitComparisonExpr(self, ctx:ListLangParser.ComparisonExprContext):
        pass


    # Enter a parse tree produced by ListLangParser#ReadCall.
    def enterReadCall(self, ctx:ListLangParser.ReadCallContext):
        pass

    # Exit a parse tree produced by ListLangParser#ReadCall.
    def exitReadCall(self, ctx:ListLangParser.ReadCallContext):
        pass


    # Enter a parse tree produced by ListLangParser#AppendExpr.
    def enterAppendExpr(self, ctx:ListLangParser.AppendExprContext):
        pass

    # Exit a parse tree produced by ListLangParser#AppendExpr.
    def exitAppendExpr(self, ctx:ListLangParser.AppendExprContext):
        pass


    # Enter a parse tree produced by ListLangParser#UnaryMinus.
    def enterUnaryMinus(self, ctx:ListLangParser.UnaryMinusContext):
        pass

    # Exit a parse tree produced by ListLangParser#UnaryMinus.
    def exitUnaryMinus(self, ctx:ListLangParser.UnaryMinusContext):
        pass


    # Enter a parse tree produced by ListLangParser#ListAccessExpr.
    def enterListAccessExpr(self, ctx:ListLangParser.ListAccessExprContext):
        pass

    # Exit a parse tree produced by ListLangParser#ListAccessExpr.
    def exitListAccessExpr(self, ctx:ListLangParser.ListAccessExprContext):
        pass


    # Enter a parse tree produced by ListLangParser#DequeueCall.
    def enterDequeueCall(self, ctx:ListLangParser.DequeueCallContext):
        pass

    # Exit a parse tree produced by ListLangParser#DequeueCall.
    def exitDequeueCall(self, ctx:ListLangParser.DequeueCallContext):
        pass


    # Enter a parse tree produced by ListLangParser#DivideExpr.
    def enterDivideExpr(self, ctx:ListLangParser.DivideExprContext):
        pass

    # Exit a parse tree produced by ListLangParser#DivideExpr.
    def exitDivideExpr(self, ctx:ListLangParser.DivideExprContext):
        pass


    # Enter a parse tree produced by ListLangParser#LenCall.
    def enterLenCall(self, ctx:ListLangParser.LenCallContext):
        pass

    # Exit a parse tree produced by ListLangParser#LenCall.
    def exitLenCall(self, ctx:ListLangParser.LenCallContext):
        pass


    # Enter a parse tree produced by ListLangParser#UnaryNot.
    def enterUnaryNot(self, ctx:ListLangParser.UnaryNotContext):
        pass

    # Exit a parse tree produced by ListLangParser#UnaryNot.
    def exitUnaryNot(self, ctx:ListLangParser.UnaryNotContext):
        pass


    # Enter a parse tree produced by ListLangParser#PlusExpr.
    def enterPlusExpr(self, ctx:ListLangParser.PlusExprContext):
        pass

    # Exit a parse tree produced by ListLangParser#PlusExpr.
    def exitPlusExpr(self, ctx:ListLangParser.PlusExprContext):
        pass


    # Enter a parse tree produced by ListLangParser#StructFieldAccessExpr.
    def enterStructFieldAccessExpr(self, ctx:ListLangParser.StructFieldAccessExprContext):
        pass

    # Exit a parse tree produced by ListLangParser#StructFieldAccessExpr.
    def exitStructFieldAccessExpr(self, ctx:ListLangParser.StructFieldAccessExprContext):
        pass


    # Enter a parse tree produced by ListLangParser#LambdaExpressionActual.
    def enterLambdaExpressionActual(self, ctx:ListLangParser.LambdaExpressionActualContext):
        pass

    # Exit a parse tree produced by ListLangParser#LambdaExpressionActual.
    def exitLambdaExpressionActual(self, ctx:ListLangParser.LambdaExpressionActualContext):
        pass


    # Enter a parse tree produced by ListLangParser#PrimaryExpressionActual.
    def enterPrimaryExpressionActual(self, ctx:ListLangParser.PrimaryExpressionActualContext):
        pass

    # Exit a parse tree produced by ListLangParser#PrimaryExpressionActual.
    def exitPrimaryExpressionActual(self, ctx:ListLangParser.PrimaryExpressionActualContext):
        pass


    # Enter a parse tree produced by ListLangParser#LogicalExpr.
    def enterLogicalExpr(self, ctx:ListLangParser.LogicalExprContext):
        pass

    # Exit a parse tree produced by ListLangParser#LogicalExpr.
    def exitLogicalExpr(self, ctx:ListLangParser.LogicalExprContext):
        pass


    # Enter a parse tree produced by ListLangParser#MinusExpr.
    def enterMinusExpr(self, ctx:ListLangParser.MinusExprContext):
        pass

    # Exit a parse tree produced by ListLangParser#MinusExpr.
    def exitMinusExpr(self, ctx:ListLangParser.MinusExprContext):
        pass


    # Enter a parse tree produced by ListLangParser#ParenExpression.
    def enterParenExpression(self, ctx:ListLangParser.ParenExpressionContext):
        pass

    # Exit a parse tree produced by ListLangParser#ParenExpression.
    def exitParenExpression(self, ctx:ListLangParser.ParenExpressionContext):
        pass


    # Enter a parse tree produced by ListLangParser#FunctionCallExpression.
    def enterFunctionCallExpression(self, ctx:ListLangParser.FunctionCallExpressionContext):
        pass

    # Exit a parse tree produced by ListLangParser#FunctionCallExpression.
    def exitFunctionCallExpression(self, ctx:ListLangParser.FunctionCallExpressionContext):
        pass


    # Enter a parse tree produced by ListLangParser#LiteralExpression.
    def enterLiteralExpression(self, ctx:ListLangParser.LiteralExpressionContext):
        pass

    # Exit a parse tree produced by ListLangParser#LiteralExpression.
    def exitLiteralExpression(self, ctx:ListLangParser.LiteralExpressionContext):
        pass


    # Enter a parse tree produced by ListLangParser#IdentifierExpression.
    def enterIdentifierExpression(self, ctx:ListLangParser.IdentifierExpressionContext):
        pass

    # Exit a parse tree produced by ListLangParser#IdentifierExpression.
    def exitIdentifierExpression(self, ctx:ListLangParser.IdentifierExpressionContext):
        pass


    # Enter a parse tree produced by ListLangParser#LambdaReturn.
    def enterLambdaReturn(self, ctx:ListLangParser.LambdaReturnContext):
        pass

    # Exit a parse tree produced by ListLangParser#LambdaReturn.
    def exitLambdaReturn(self, ctx:ListLangParser.LambdaReturnContext):
        pass


    # Enter a parse tree produced by ListLangParser#LambdaBlock.
    def enterLambdaBlock(self, ctx:ListLangParser.LambdaBlockContext):
        pass

    # Exit a parse tree produced by ListLangParser#LambdaBlock.
    def exitLambdaBlock(self, ctx:ListLangParser.LambdaBlockContext):
        pass


    # Enter a parse tree produced by ListLangParser#literal.
    def enterLiteral(self, ctx:ListLangParser.LiteralContext):
        pass

    # Exit a parse tree produced by ListLangParser#literal.
    def exitLiteral(self, ctx:ListLangParser.LiteralContext):
        pass


    # Enter a parse tree produced by ListLangParser#listLiteral.
    def enterListLiteral(self, ctx:ListLangParser.ListLiteralContext):
        pass

    # Exit a parse tree produced by ListLangParser#listLiteral.
    def exitListLiteral(self, ctx:ListLangParser.ListLiteralContext):
        pass


    # Enter a parse tree produced by ListLangParser#structLiteral.
    def enterStructLiteral(self, ctx:ListLangParser.StructLiteralContext):
        pass

    # Exit a parse tree produced by ListLangParser#structLiteral.
    def exitStructLiteral(self, ctx:ListLangParser.StructLiteralContext):
        pass


    # Enter a parse tree produced by ListLangParser#fieldAssignment.
    def enterFieldAssignment(self, ctx:ListLangParser.FieldAssignmentContext):
        pass

    # Exit a parse tree produced by ListLangParser#fieldAssignment.
    def exitFieldAssignment(self, ctx:ListLangParser.FieldAssignmentContext):
        pass



del ListLangParser