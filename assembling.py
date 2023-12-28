"A simple module for creating simple assemblers.\n\nProvides classes like `Instruction`, `InstructionSet`, `Assembler` and `AssemblerError`."

import re

class Instruction:
    "Represents a instruction with a mnemonic, the patterns that define how arguments can be taken (in `re`'s regular expressions' syntax) and a function which can take the previously mentioned arguments as theirs and return a string (which will be used for compilation)."
    def __init__(self, mnemonic: str, *arguments: re.Pattern | str, formatter: callable) -> None:
        "Represents a instruction with a mnemonic, the patterns that define how arguments can be taken (in `re`'s regular expressions' syntax) and a function which can take the previously mentioned arguments as theirs and return a string (which will be used for compilation)."
        self.mnemonic, self.arguments, self.formatter = mnemonic, arguments, formatter
        arguments_regex = r"(?:" + r'\s*,\s*'.join(f"({arg_syntax})" for arg_syntax in arguments) + r")"
        self.pattern_str = fr"(?:\s*{re.escape(mnemonic)}\s*{arguments_regex}\s*)"
    
    def pattern(self) -> str:
        "Returns the full pattern of the instruction."
        return self.pattern_str
    
    def format(self, *arguments: str) -> str:
        "Returns the result of calling the formatting function of the instruction with the given arguments."
        return self.formatter(*arguments)
    
    def __repr__(self) -> str:
        return f"Instruction({self.mnemonic!r}, {', '.join(repr(a) for a in self.arguments)}, formatter={self.formatter!r})"

class InstructionSet:
    "Represents an instruction set that accepts two functions for defining what to do whenever a section starts or ends (accepting the section name as a parameter) as well as the instructions."
    def __init__(self, section_start_formatter: callable, section_end_formatter: callable, *instructions: Instruction) -> None:
        "Represents an instruction set that accepts two functions for defining what to do whenever a section starts or ends (accepting the section name as a parameter) as well as the instructions."
        self.instructions = tuple(instructions)
        self.section_start_formatter = section_start_formatter
        self.section_end_formatter = section_end_formatter

    def __iter__(self):
        return iter(self.instructions)
    
    def __repr__(self) -> str:
        return f"InstructionSet({self.section_start_formatter!r}, {self.section_end_formatter!r}, {', '.join(repr(i) for i in self.instructions)})"

class AssemblerError(SyntaxError):
    "Invalid syntax according to the provided instruction set."
    ...

class Assembler:
    "Represents an assembler capable of translating code based on two strings, which define what to write on the start of the result, as well as the provided instruction set."
    def __init__(self, start_formatter: str, end_formatter: str, instruction_set: InstructionSet) -> None:
        "Represents an assembler capable of translating code based on two strings, which define what to write on the start of the result, as well as the provided instruction set."
        self.instruction_set = instruction_set
        self.start_formatter = start_formatter
        self.end_formatter = end_formatter
    
    def assemble(self, text: str, binary_output: bool = False) -> str | bytes:
        "Assembles the given text and returns the result."
        if not text.strip(): raise AssemblerError("no code to assemble")
        result = []
        sections_started = 0
        new_text = []
        to_jump = []

        for line_number, line in enumerate((re.sub(r";.*", "", text)).splitlines()):
            if (_s := re.fullmatch(r"\s*((?:_|\w)(?:_|\w|\d)*)\s*:(.*)", line)):
                statement = _s.groups()[1]
                if re.fullmatch(r"\s*((?:_|\w)(?:_|\w|\d)*)\s*:(.*)", statement): raise AssemblerError("can't have a more than one label in one line; separate labels with newlines")
                new_text.append(line[:len(line) - len(statement)]); to_jump.append(line_number)
                new_text.append(statement); to_jump.append(line_number)
            else:
                new_text.append(line); to_jump.append(line_number)
        
        new_text = "\n".join(new_text)
        last_section_name = ""

        for line_number, line in enumerate((re.sub(r";.*", "", new_text)).splitlines()):
            no_instruction_can_please_me = True
            if (s := re.fullmatch(r"\s*((?:_|\w)(?:_|\w|\d)*)\s*:\s*", line)):
                if sections_started != 0:
                    result.append(self.instruction_set.section_end_formatter(s.groups()[0]))
                sections_started += 1
                result.append(self.instruction_set.section_start_formatter(s.groups()[0]))
                last_section_name = s.groups()[0]
                no_instruction_can_please_me = False
                continue
            elif not line or not line.strip():
                no_instruction_can_please_me = False
            else:
                no_instruction_can_please_me = True
            
            # Check instructions only if the line is not empty
            if no_instruction_can_please_me:
                for instruction in self.instruction_set:
                    instruction_pattern = instruction.pattern()
                    if (i := re.fullmatch(instruction_pattern, line)):
                        if not sections_started:
                            raise AssemblerError(f"statement in line {line_number + 1} out of section")
                        result.append(instruction.format(*i.groups()))
                        no_instruction_can_please_me = False
                        break  # Exit the loop if an instruction matches
                if no_instruction_can_please_me:
                    raise AssemblerError(f"invalid syntax at line {line_number + 1} (as specified by given instruction set)")
                
        try: result.append(self.instruction_set.section_end_formatter(last_section_name))
        except AttributeError: ...
        _result = "\n".join(filter(None, [self.start_formatter] + result + [self.end_formatter]))
        return bytes(_result) if binary_output else str(_result)
    
    def __repr__(self) -> str:
        return f"Assembler({self.instruction_set!r})"