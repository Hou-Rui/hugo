#!/usr/bin/env python3
import sys


class Stack(list):
    """ 实现通用栈。 """

    def push(self, x):
        """ 压入栈。 """
        self.append(x)

    def top(self):
        """ 栈顶。 """
        return self[len(self) - 1]


class Error(Exception):
    """ 解释程序错误类。 """

    def __init__(self, line: int, msg: str):
        """
        初始化。
        :param line: 错误行号。
        :param msg: 错误信息。
        """
        self.line = line + 1
        self.msg = msg

    def print_message(self):
        """ 显示错误信息。 """
        print('ERROR (line %d): %s' % (self.line, self.msg))


class Lexer:
    """ 简易词法解析器，产生记号。 """

    def is_closed(self, string: str) -> bool:
        """
        判断字符串中括号是否闭合。
        :param str: 待判断字符串。
        """
        pairs = ('(', ')'), ('[', ']'), ('{', '}')
        for begin, end in pairs:
            if string.count(begin) != string.count(end):
                return False
        return True

    def tokenize(self, line: str) -> list:
        """
        词法解析，以逗号分隔产生记号列表。函数中的逗号不计。
        :param line: 待解析字符串。
        :returns: 记号列表。
        """
        split_symbols = ','
        result = []
        token = ''
        in_string = False
        for c in line:
            # 字符串开始或结束
            if c == '"':
                in_string = not in_string
                if not in_string:
                    result.append(token.strip())
                    token = ''
            # 字符串视为一个记号，不带引号
            elif in_string:
                token += c
            # 括号闭合，记号结束
            elif c == split_symbols and self.is_closed(token):
                result.append(token.strip())
                token = ''
            # 记号未结束
            else:
                token += c
        # 压入最后一个记号
        if token:
            result.append(token.strip())
        return result


class Interpreter:
    """ 解释器类。 """

    def __init__(self):
        """ 初始化。 """
        self.lexer = Lexer()
        self.var_table = {}
        self.label_table = {}
        self.call_stack = Stack()
        self.goto_stack = Stack()
        self.if_stack = Stack()
        self.while_stack = Stack()
        self.while_lines = set()

    def load(self, filename: str):
        """
        加载文件，并预处理标签表。
        :param filename: 文件名。
        """
        prog_file = open(filename)
        self.program = prog_file.readlines()
        # 处理标签
        for i in range(len(self.program)):
            line = self.program[i].strip()
            if line.startswith(':'):
                label_name = line[1:].strip()
                self.label_table[label_name] = i
        # 添加 EOF 标签
        self.label_table['EOF'] = len(self.program)

    def replace_marco(self, line_cnt: int, line: str) -> str:
        """
        替换字符串中的变量。
        :param line_cnt: 行号。
        :param line: 待替换字符串。
        :returns: 替换后的字符串。
        """
        in_macro = False
        macro_name = ''
        result = ''
        for c in line:
            if c == '$':
                in_macro = not in_macro
                if not in_macro:
                    try:
                        result += self.var_table[macro_name]
                    except KeyError:
                        pass  # 未定义的变量视为空
                    macro_name = ''
            elif in_macro:
                macro_name += c
            else:
                result += c
        if macro_name:
            result += '%' + macro_name
        return result

    def parse_command(self, line_cnt: int, line: str) -> (str, list):
        """
        解析命令行。
        :param line_cnt: 行号。
        :param line: 命令行字符串。
        :returns: 命令名和参数列表。
        """
        line = self.replace_marco(line_cnt, line)
        cmd, *args = line.split(' ')
        cmd = cmd.upper()
        args = [x.strip() for x in self.lexer.tokenize(' '.join(args))]
        return cmd, args

    def exec_command(self, line_cnt: int, cmd: str, args: list) -> int:
        """
        执行命令。
        :param line_cnt: 行号。
        :param cmd: 命令名。
        :param args: 参数列表。
        """
        # 处理 PAUSE 语句
        if cmd == 'PAUSE':
            input('...')
        # 处理 ECHO 语句
        elif cmd == 'ECHO':
            for item in args:
                print(item, end=' ')
            print()
        # 处理 PRINT 语句
        elif cmd == 'PRINT':
            for item in args:
                print(item, end=' ')
        # 处理 SET 语句
        elif cmd == 'SET':
            for arg in args:
                key, value = (x.strip() for x in arg.split('='))
                self.var_table[key] = value
        # 处理 LET 语句
        elif cmd == 'LET':
            for arg in args:
                key, expr = (x.strip() for x in arg.split('='))
                self.var_table[key] = str(eval(expr)).strip()
        # 处理 INPUT 语句
        elif cmd == 'INPUT':
            for key in args:
                value = input().strip()
                self.var_table[key] = value
        # 处理 SWAP 语句
        elif cmd == 'SWAP':
            key1, key2 = args[0], args[1]
            self.var_table[key1], self.var_table[key2] \
            = self.var_table[key2], self.var_table[key1]
        # 处理 GOTO 语句
        elif cmd == 'GOTO':
            try:
                label_name = args[0]
                label = self.label_table[label_name]
            except KeyError:
                raise Error(line_cnt, 'unknown label %s' % label_name)
            self.goto_stack.push(label)
        # 处理 CALL 语句
        elif cmd == 'CALL':
            try:
                label_name = args[0]
                label = self.label_table[label_name]
            except KeyError:
                raise Error(line_cnt, 'unknown label %s' % label_name)
            self.goto_stack.push(self.label_table[label_name])
            self.call_stack.push(line_cnt + 1)
        # 处理 RETURN 语句
        elif cmd == 'RETURN':
            self.goto_stack.push(self.label_table['EOF'])
        # 处理 EXIT 语句
        elif cmd == 'EXIT':
            sys.exit(0)
        return 0

    def run(self):
        """ 执行程序。 """
        i = 0
        while i < len(self.program):
            # 去除前后空格
            line = self.program[i].strip()
            # 忽略空行和注释行
            if not line or line.startswith('#'):
                i += 1
                continue
            # 解析命令行
            cmd, args = self.parse_command(i, line)

            # 处理 END 语句
            if cmd == 'END':
                if self.if_stack:
                    self.if_stack.pop()
                    i += 1
                    continue
                raise Error(i, 'extra END')
            # 处理 WEND 语句
            if cmd == 'WEND':
                if self.while_stack:
                    data = self.while_stack.pop()
                    if not data[0]:
                        i += 1
                        continue
                    i = self.label_table['__while_label_%d__' % data[1]]
                    continue
                raise Error(i, 'extra WEND')
            # 处理 WHILE 语句
            if cmd == 'WHILE':
                if i not in self.while_lines:
                    self.label_table['__while_label_%d__' % i] = i
                    self.while_lines.add(i)
                result = False
                if (not self.while_stack) or self.while_stack.top()[0]:
                    result = eval(args[0])
                self.while_stack.push((bool(result), i))
                i += 1
                continue
            # 处理 IF 语句
            if cmd == 'IF':
                result = False
                if (not self.if_stack) or self.if_stack.top():
                    result = eval(args[0])
                self.if_stack.push(bool(result))
                i += 1
                continue
            # 处理 ELSE 语句
            if cmd == 'ELSE':
                if not self.if_stack:
                    raise Error(i, 'ELSE without IF')
                if len(args) > 0 and args[0].upper() == 'IF':
                    if not self.if_stack.pop():
                        result = eval(args[1])
                    self.if_stack.push(bool(result))
                    i += 1
                    continue
                self.if_stack.push(not self.if_stack.pop())
                i += 1
                continue
            # 处理 WHILE 栈
            if self.while_stack and not self.while_stack.top()[0]:
                i += 1
                continue
            # 处理 IF 栈
            if self.if_stack and not self.if_stack.top():
                i += 1
                continue

            # 执行命令行
            ret_value = self.exec_command(i, cmd, args)
            self.exec_command(i, 'SET', ['ERRORLEVEL=%d' % ret_value])
            i += 1
            # 处理跳转操作
            if self.goto_stack:
                i = self.goto_stack.pop()
            if i >= len(self.program) and self.call_stack:
                i = self.call_stack.pop()


def main():
    my = Interpreter()
    my.load("luogu1014.hugo")
    try:
        my.run()
    except Error as error:
        error.print_message()


if __name__ == '__main__':
    main()
