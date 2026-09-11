"""Language map so JARVIS can write more than Python."""

LANGS = {
    "python": ("py", "python"),
    "py": ("py", "python"),
    "javascript": ("js", "javascript"),
    "js": ("js", "javascript"),
    "typescript": ("ts", "typescript"),
    "ts": ("ts", "typescript"),
    "html": ("html", "html"),
    "css": ("css", "css"),
    "java": ("java", "java"),
    "c#": ("cs", "csharp"),
    "csharp": ("cs", "csharp"),
    "c++": ("cpp", "cpp"),
    "cpp": ("cpp", "cpp"),
    "c": ("c", "c"),
    "go": ("go", "go"),
    "golang": ("go", "go"),
    "rust": ("rs", "rust"),
    "php": ("php", "php"),
    "ruby": ("rb", "ruby"),
    "swift": ("swift", "swift"),
    "kotlin": ("kt", "kotlin"),
    "sql": ("sql", "sql"),
    "bash": ("sh", "bash"),
    "shell": ("sh", "bash"),
    "powershell": ("ps1", "powershell"),
    "lua": ("lua", "lua"),
    "r": ("r", "r"),
    "json": ("json", "json"),
    "yaml": ("yml", "yaml"),
    "xml": ("xml", "xml"),
    "dart": ("dart", "dart"),
    "scala": ("scala", "scala"),
    "haskell": ("hs", "haskell"),
    "matlab": ("m", "matlab"),
    "perl": ("pl", "perl"),
    "assembly": ("asm", "asm"),
    "vue": ("vue", "javascript"),
    "react": ("jsx", "javascript"),
    "jsx": ("jsx", "javascript"),
}


def detect(text: str) -> tuple[str, str]:
    low = (text or "").lower()
    for key in sorted(LANGS, key=len, reverse=True):
        if re_word(key, low):
            return LANGS[key]
    return ("py", "python")


def re_word(key: str, low: str) -> bool:
    import re

    if key in {"c", "r"}:
        return bool(re.search(rf"(?:^|\s){re.escape(key)}(?:\s|$|\+|\#)", low))
    return bool(re.search(rf"\b{re.escape(key)}\b", low))


def scaffold(ext: str, lang: str, job: str) -> str:
    job = (job or "task").strip()
    desc = job[:200]
    table = {
        "py": (
            f'"""{desc}"""\n\n'
            "def main():\n"
            f"    print({desc!r})\n\n"
            "if __name__ == '__main__':\n"
            "    main()\n"
        ),
        "js": f"// {desc}\nfunction main() {{\n  console.log({desc!r});\n}}\n\nmain();\n",
        "ts": f"// {desc}\nfunction main(): void {{\n  console.log({desc!r});\n}}\n\nmain();\n",
        "jsx": (
            f"// {desc}\nexport default function App() {{\n"
            f"  return <div>{desc}</div>;\n}}\n"
        ),
        "html": (
            "<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n"
            f"  <meta charset=\"utf-8\">\n  <title>{desc}</title>\n"
            "  <style>body{font-family:sans-serif;padding:2rem}</style>\n"
            f"</head>\n<body>\n  <h1>{desc}</h1>\n</body>\n</html>\n"
        ),
        "css": f"/* {desc} */\n:root {{ --accent: #e8c547; }}\nbody {{ margin: 0; font-family: sans-serif; }}\n",
        "java": (
            f"// {desc}\npublic class Main {{\n"
            "  public static void main(String[] args) {\n"
            f"    System.out.println({desc!r});\n  }}\n}}\n"
        ),
        "cs": (
            f"// {desc}\nusing System;\nclass Program {{\n"
            f"  static void Main() => Console.WriteLine({desc!r});\n}}\n"
        ),
        "cpp": (
            f"// {desc}\n#include <iostream>\nint main() {{\n"
            f"  std::cout << {desc!r} << std::endl;\n  return 0;\n}}\n"
        ),
        "c": (
            f"/* {desc} */\n#include <stdio.h>\nint main(void) {{\n"
            f"  puts({desc!r});\n  return 0;\n}}\n"
        ),
        "go": (
            f"// {desc}\npackage main\nimport \"fmt\"\n"
            f"func main() {{ fmt.Println({desc!r}) }}\n"
        ),
        "rs": (
            f"// {desc}\nfn main() {{\n    println!({desc!r});\n}}\n"
        ),
        "php": f"<?php\n// {desc}\necho {desc!r};\n",
        "rb": f"# {desc}\nputs {desc!r}\n",
        "swift": f"// {desc}\nprint({desc!r})\n",
        "kt": f"// {desc}\nfun main() {{\n    println({desc!r})\n}}\n",
        "sql": f"-- {desc}\nSELECT '{desc.replace(chr(39), '')}' AS result;\n",
        "sh": f"#!/usr/bin/env bash\n# {desc}\necho {desc!r}\n",
        "ps1": f"# {desc}\nWrite-Output {desc!r}\n",
        "lua": f"-- {desc}\nprint({desc!r})\n",
        "r": f"# {desc}\ncat({desc!r}, '\\n')\n",
        "json": (
            "{\n  \"task\": %s,\n  \"ok\": true\n}\n" % __import__("json").dumps(desc)
        ),
        "yml": f"task: {desc}\nok: true\n",
        "xml": f'<?xml version="1.0"?>\n<task>{desc}</task>\n',
        "dart": f"// {desc}\nvoid main() {{\n  print({desc!r});\n}}\n",
        "scala": f"// {desc}\nobject Main extends App {{\n  println({desc!r})\n}}\n",
        "hs": f"-- {desc}\nmain = putStrLn {desc!r}\n",
        "m": f"% {desc}\ndisp({desc!r});\n",
        "pl": f"# {desc}\nprint {desc!r}, \"\\n\";\n",
        "asm": f"; {desc}\nsection .text\nglobal _start\n_start:\n    mov eax, 1\n    int 0x80\n",
        "vue": (
            f"<template>\n  <div>{desc}</div>\n</template>\n"
            "<script>\nexport default { name: 'App' }\n</script>\n"
        ),
    }
    return table.get(ext, f"// {lang}: {desc}\n")
