# Generated from ListLang.g4 by ANTLR 4.13.2
from antlr4 import *
if "." in __name__:
    from .ListLangParser import ListLangParser
else:
    from ListLangParser import ListLangParser

# This class defines a complete generic visitor for a parse tree produced by ListLangParser.

class ListLangVisitor(ParseTreeVisitor):

    # Visit a parse tree produced by ListLangParser#program.
    def visitProgram(self, ctx:ListLangParser.ProgramContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by ListLangParser#functionDecl.
    def visitFunctionDecl(self, ctx:ListLangParser.FunctionDeclContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by ListLangParser#parameterList.
    def visitParameterList(self, ctx:ListLangParser.ParameterListContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by ListLangParser#parameter.
    def visitParameter(self, ctx:ListLangParser.ParameterContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by ListLangParser#identifierList.
    def visitIdentifierList(self, ctx:ListLangParser.IdentifierListContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by ListLangParser#ExpressionRightAssignment.
    def visitExpressionRightAssignment(self, ctx:ListLangParser.ExpressionRightAssignmentContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by ListLangParser#IdentifierLeftAssignment.
    def visitIdentifierLeftAssignment(self, ctx:ListLangParser.IdentifierLeftAssignmentContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by ListLangParser#IdentifierAssignExpression.
    def visitIdentifierAssignExpression(self, ctx:ListLangParser.IdentifierAssignExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by ListLangParser#ListElementAssignment.
    def visitListElementAssignment(self, ctx:ListLangParser.ListElementAssignmentContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by ListLangParser#ListElementAssignExpression.
    def visitListElementAssignExpression(self, ctx:ListLangParser.ListElementAssignExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by ListLangParser#StructFieldAssignment.
    def visitStructFieldAssignment(self, ctx:ListLangParser.StructFieldAssignmentContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by ListLangParser#StructFieldAssignExpression.
    def visitStructFieldAssignExpression(self, ctx:ListLangParser.StructFieldAssignExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by ListLangParser#multiAssignment.
    def visitMultiAssignment(self, ctx:ListLangParser.MultiAssignmentContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by ListLangParser#assignmentStatement.
    def visitAssignmentStatement(self, ctx:ListLangParser.AssignmentStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by ListLangParser#statement.
    def visitStatement(self, ctx:ListLangParser.StatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by ListLangParser#breakStatement.
    def visitBreakStatement(self, ctx:ListLangParser.BreakStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by ListLangParser#continueStatement.
    def visitContinueStatement(self, ctx:ListLangParser.ContinueStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by ListLangParser#statementBlock.
    def visitStatementBlock(self, ctx:ListLangParser.StatementBlockContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by ListLangParser#ifStatement.
    def visitIfStatement(self, ctx:ListLangParser.IfStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by ListLangParser#whileStatement.
    def visitWhileStatement(self, ctx:ListLangParser.WhileStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by ListLangParser#doUntilStatement.
    def visitDoUntilStatement(self, ctx:ListLangParser.DoUntilStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by ListLangParser#forStatement.
    def visitForStatement(self, ctx:ListLangParser.ForStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by ListLangParser#switchStatement.
    def visitSwitchStatement(self, ctx:ListLangParser.SwitchStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by ListLangParser#caseClause.
    def visitCaseClause(self, ctx:ListLangParser.CaseClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by ListLangParser#returnStatement.
    def visitReturnStatement(self, ctx:ListLangParser.ReturnStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by ListLangParser#writeStatement.
    def visitWriteStatement(self, ctx:ListLangParser.WriteStatementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by ListLangParser#argument.
    def visitArgument(self, ctx:ListLangParser.ArgumentContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by ListLangParser#argumentList.
    def visitArgumentList(self, ctx:ListLangParser.ArgumentListContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by ListLangParser#functionCall.
    def visitFunctionCall(self, ctx:ListLangParser.FunctionCallContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by ListLangParser#expressionList.
    def visitExpressionList(self, ctx:ListLangParser.ExpressionListContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by ListLangParser#MultiplyExpr.
    def visitMultiplyExpr(self, ctx:ListLangParser.MultiplyExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by ListLangParser#ComparisonExpr.
    def visitComparisonExpr(self, ctx:ListLangParser.ComparisonExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by ListLangParser#ReadCall.
    def visitReadCall(self, ctx:ListLangParser.ReadCallContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by ListLangParser#AppendExpr.
    def visitAppendExpr(self, ctx:ListLangParser.AppendExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by ListLangParser#UnaryMinus.
    def visitUnaryMinus(self, ctx:ListLangParser.UnaryMinusContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by ListLangParser#ListAccessExpr.
    def visitListAccessExpr(self, ctx:ListLangParser.ListAccessExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by ListLangParser#DequeueCall.
    def visitDequeueCall(self, ctx:ListLangParser.DequeueCallContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by ListLangParser#DivideExpr.
    def visitDivideExpr(self, ctx:ListLangParser.DivideExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by ListLangParser#LenCall.
    def visitLenCall(self, ctx:ListLangParser.LenCallContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by ListLangParser#UnaryNot.
    def visitUnaryNot(self, ctx:ListLangParser.UnaryNotContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by ListLangParser#PlusExpr.
    def visitPlusExpr(self, ctx:ListLangParser.PlusExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by ListLangParser#StructFieldAccessExpr.
    def visitStructFieldAccessExpr(self, ctx:ListLangParser.StructFieldAccessExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by ListLangParser#LambdaExpressionActual.
    def visitLambdaExpressionActual(self, ctx:ListLangParser.LambdaExpressionActualContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by ListLangParser#PrimaryExpressionActual.
    def visitPrimaryExpressionActual(self, ctx:ListLangParser.PrimaryExpressionActualContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by ListLangParser#LogicalExpr.
    def visitLogicalExpr(self, ctx:ListLangParser.LogicalExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by ListLangParser#MinusExpr.
    def visitMinusExpr(self, ctx:ListLangParser.MinusExprContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by ListLangParser#ParenExpression.
    def visitParenExpression(self, ctx:ListLangParser.ParenExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by ListLangParser#FunctionCallExpression.
    def visitFunctionCallExpression(self, ctx:ListLangParser.FunctionCallExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by ListLangParser#LiteralExpression.
    def visitLiteralExpression(self, ctx:ListLangParser.LiteralExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by ListLangParser#IdentifierExpression.
    def visitIdentifierExpression(self, ctx:ListLangParser.IdentifierExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by ListLangParser#LambdaReturn.
    def visitLambdaReturn(self, ctx:ListLangParser.LambdaReturnContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by ListLangParser#LambdaBlock.
    def visitLambdaBlock(self, ctx:ListLangParser.LambdaBlockContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by ListLangParser#literal.
    def visitLiteral(self, ctx:ListLangParser.LiteralContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by ListLangParser#listLiteral.
    def visitListLiteral(self, ctx:ListLangParser.ListLiteralContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by ListLangParser#structLiteral.
    def visitStructLiteral(self, ctx:ListLangParser.StructLiteralContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by ListLangParser#fieldAssignment.
    def visitFieldAssignment(self, ctx:ListLangParser.FieldAssignmentContext):
        return self.visitChildren(ctx)



del ListLangParser