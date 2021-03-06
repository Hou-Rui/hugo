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

    pairs = ('(', ')'), ('[', ']'), ('{', '}')

    def is_closed(self, string: str) -> bool:
        """
        判断字符串中括号是否闭合。
        :param str: 待判断字符串。
        """
        for begin, end in self.pairs:
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

    var_end_table = [
        ' ', '\n', '\t', '\r',
        ',', '+', '-', '*', '/', '%',
        '$'
    ]

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

    def evaluate(self, expr: str) -> object:
        expr = expr.replace(' mod ', ' % ')
        allowed_objects = {
            'abs': abs, 'min': min, 'max': max
        }
        return eval(expr, allowed_objects)

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
        if not line.endswith('\n'):
            line += '\n'
        for c in line:
            if not in_macro and c == '$':
                in_macro = True
            elif in_macro and c in self.var_end_table:
                try:
                    data = macro_name.split(':')
                    if len(data) == 1:
                        result += self.var_table[macro_name]
                    else:
                        head, cnt = data[0], int(data[1])
                        array = self.var_table[head].split(' ')
                        if cnt >= len(array):
                            raise Error(line_cnt, 'array subscript over-bounded')
                        result += array[cnt]
                except KeyError:
                    pass  # 未定义的变量视为空
                finally:
                    in_macro = False
                    result += c
                    macro_name = ''
            elif in_macro:
                macro_name += c
            else:
                result += c
        # 去掉额外添加的'\n'
        return result.strip()

    def parse_command(self, line_cnt: int, line: str) -> (str, list):
        """
        解析命令行。
        :param line_cnt: 行号。
        :param line: 命令行字符串。
        :returns: 命令名和参数列表。
        """
        line = self.replace_marco(line_cnt, line)
        cmd, *args = line.split(' ')
        cmd = cmd.upper().strip()
        args = [x.strip() for x in self.lexer.tokenize(' '.join(args))]
        return cmd, args

    def exec_command(self, line_cnt: int, cmd: str, args: list) -> int:
        """
        执行命令。
        :param line_cnt: 行号。
        :param cmd: 命令名。
        :param args: 参数列表。
        """
        if cmd == 'PAUSE':
            self.exec_pause(args)
        elif cmd == 'ECHO':
            self.exec_echo(args)
        elif cmd == 'PRINT':
            self.exec_print(args)
        elif cmd == 'SET':
            self.exec_set(args)
        elif cmd == 'LET':
            self.exec_let(args)
        elif cmd == 'INPUT':
            self.exec_input(args)
        elif cmd == 'INC':
            self.exec_inc(args)
        elif cmd == 'DEC':
            self.exec_dec(args)
        elif cmd == 'SWAP':
            self.exec_swap(args)
        elif cmd == 'GOTO':
            self.exec_goto(args, line_cnt)
        elif cmd == 'CALL':
            self.exec_call(args, line_cnt)
        elif cmd == 'RETURN':
            self.exec_return()
        elif cmd == 'EXIT':
            self.exec_exit()
        return 0

    def exec_exit(self):
        sys.exit(0)

    def exec_return(self):
        self.goto_stack.push(self.label_table['EOF'])

    def exec_call(self, args, line_cnt):
        try:
            label_name = args[0]
            label = self.label_table[label_name]
        except KeyError:
            raise Error(line_cnt, 'unknown label %s' % label_name)
        self.goto_stack.push(label)
        self.call_stack.push(line_cnt + 1)

    def exec_goto(self, args, line_cnt):
        try:
            label_name = args[0]
            label = self.label_table[label_name]
        except KeyError:
            raise Error(line_cnt, 'unknown label %s' % label_name)
        self.goto_stack.push(label)

    def exec_swap(self, args):
        key1, key2 = args[0], args[1]
        self.var_table[key1], self.var_table[key2] \
        = self.var_table[key2], self.var_table[key1]

    def exec_dec(self, args):
        try:
            key = args[0]
            self.var_table[key] = str(int(self.var_table[key]) - 1)
        except KeyError:
            self.var_table[key] = '-1'

    def exec_inc(self, args):
        try:
            key = args[0]
            self.var_table[key] = str(int(self.var_table[key]) + 1)
        except KeyError:
            self.var_table[key] = '1'

    def exec_input(self, args):
        for key in args:
            value = input().strip()
            self.var_table[key] = value

    def exec_let(self, args):
        for arg in args:
            key, expr = (x.strip() for x in arg.split('='))
            self.var_table[key] = str(self.evaluate(expr)).strip()

    def exec_set(self, args):
        for arg in args:
            key, value = (x.strip() for x in arg.split('='))
            self.var_table[key] = value

    def exec_print(self, args):
        for item in args:
            print(item, end=' ')

    def exec_echo(self, args):
        self.exec_print(args)
        print()

    def exec_pause(self, args):
        input('...')

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
                    result = self.evaluate(args[0])
                self.while_stack.push((bool(result), i))
                i += 1
                continue
            # 处理 IF 语句
            if cmd == 'IF':
                result = False
                if (not self.if_stack) or self.if_stack.top():
                    result = self.evaluate(args[0])
                self.if_stack.push(bool(result))
                i += 1
                continue
            # 处理 ELSE 语句
            if cmd == 'ELSE':
                if not self.if_stack:
                    raise Error(i, 'ELSE without IF')
                if len(args) > 0 and args[0].upper() == 'IF':
                    if not self.if_stack.pop():
                        result = self.evaluate(args[1])
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
    #prog_name = sys.argv[1]
    #my.load(prog_name)
    my.load('luogu1014.hugo')
    try:
        my.run()
    except Error as error:
        error.print_message()


if __name__ == '__main__':
    main()
