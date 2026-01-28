1\) 1 LAB 

✅ .venv\Scripts\activate

✅ $env:PYTHONPATH = "$PWD\src"

✅ python -m task1.cli .\src\examples\ok_all_constructs.v3 .\out.dot

Ожидаемый результат:

терминале нет ошибок

B) Файл создается:

✅ dir .\out.dot

C) DOT → PNG (полное дерево)

✅ dot -Tpng .\out.dot -o .\out.png

✅ start .\out.png

D) Визуализация частичного дерева

✅ start .\out_part.png

E) Некорректный пример: отчет об ошибке в stderr (доказывает условие)

✅ python -m task1.cli .\src\examples\bad_syntax.v3 .\bad.dot

[parse error] line=... col=... и список "Expected one of …"

То есть ошибка указывается с номером строки/столбца.


2\) 2 LAB 

✅ python -m task2.cli .\src\examples\ok_all_constructs.v3 .\out2 --png --svg

✅ dir .\out2

✅ dir .\out2\graph

✅ more .\out2\call_graph.errors.txt

Откройте визуализацию CFG:

✅ start .\out2\graph\main.png

ENTRY → dim → присваивания if (x > 0) ветви True/False и join while (y > 0) стрелки цикла (True - возврат, False - выход) do_while (x > 10) блок + break → after_do → EXIT

Демо-2: Показать заполненный граф вызовов (calls_demo.v3):

✅ python -m task2.cli .\src\examples\calls_demo.v3 .\out2_calls --png --svg

✅ start .\out2_calls\call_graph.png

Если хотите, откройте также CFG функций:

✅ start .\out2_calls\graph\main_tree2.png

✅ start .\out2_calls\graph\foo.png

"показать также ошибочную ситуацию":

✅ python -m task2.cli .\src\examples\bad_syntax.v3 .\out_bad --png
more .\out_bad\call_graph.errors.txt

Ожидаемый результат: в файле call_graph.errors.txt будет ошибка с указанием строки и столбца, например [parse error] line=... col=...

3\) 3 LAB 

✅ python -m task3.cli .\src\examples\task3_demo.v3 .\out3 --asm .\out3\result_real_2addr.asm --keep-cfg

Проверка:

✅dir .\out3
  dir .\out3\graph
  Get-Content .\out3\result_real_2addr.asm -TotalCount 20 | Out-Host

3) (Доказательство) Открываем визуализацию CFG (main.png)

✅ start .\out3\graph\main.png

4) Ассемблирование: генерируем бинарный файл с variant27_2addr

✅ .\tools\ptp\Portable.RemoteTasks.Manager.exe -ul 503291 -up "b551163b-6741-4c92-b016-01f99e8a9947" -s Assemble -w `
asmListing out3\result_real_2addr.asm `
definitionFile tools\ptp\variant27_2addr.target.pdsl `
archName variant27_2addr

Отсюда появится ASSEMBLE_ID. (В вашем окне будет строка "Task Assemble started with id ...".)

4.1) Загружаем out.ptptb в правильное место
Введите ASSEMBLE_ID:

✅ .\tools\ptp\Portable.RemoteTasks.Manager.exe -ul 503291 -up "b551163b-6741-4c92-b016-01f99e8a9947" -g ASSEMBLE_ID -r out.ptptb -o out3\out_real_2addr.ptptb
dir .\out3\out_real_2addr.ptptb

5) (Доказательство) Проверяем, правильно ли отображается "code section" через дизассемблирование

✅ .\tools\ptp\Portable.RemoteTasks.Manager.exe -ul 503291 -up "b551163b-6741-4c92-b016-01f99e8a9947" -s Disassemble -w `
in.ptptb out3\out_real_2addr.ptptb `
definitionFile tools\ptp\variant27_2addr.target.pdsl `
archName variant27_2addr

Появится Task ID → загружаем файл дизассемблирования:

✅ .\tools\ptp\Portable.RemoteTasks.Manager.exe -ul 503291 -up "b551163b-6741-4c92-b016-01f99e8a9947" -g DISASM_ID -r disasmListing.txt -o out3\disasm_real_2addr.txt
Get-Content .\out3\disasm_real_2addr.txt -TotalCount 10 | Out-Host

6) Выполнение: запускаем бинарный файл + доказываем вывод из файла
 
✅ RUN_ID: "$RUNID"

.\tools\ptp\Portable.RemoteTasks.Manager.exe -ul 503291 -up "b551163b-6741-4c92-b016-01f99e8a9947" -g $RUNID -r stdout.txt -o out3\run_stdout_real_2addr.txt
.\tools\ptp\Portable.RemoteTasks.Manager.exe -ul 503291 -up "b551163b-6741-4c92-b016-01f99e8a9947" -g $RUNID -r stderr.txt -o out3\run_stderr_real_2addr.txt
.\tools\ptp\Portable.RemoteTasks.Manager.exe -ul 503291 -up "b551163b-6741-4c92-b016-01f99e8a9947" -g $RUNID -r trace.txt  -o out3\run_trace_real_2addr.txt

--- Calculator ----

1. Показать входной файл

✅ Format-Hex -Path .\out3\in.txt          Здесь, например, будет видно 02 04.

2. Запустить программу (ExecuteBinaryWithInput)

✅ .\tools\ptp\Portable.RemoteTasks.Manager.exe -ul 503291 -up "b551163b-6741-4c92-b016-01f99e8a9947" -s ExecuteBinaryWithInput -w `
stdinRegStName rin `
stdoutRegStName rout `
inputFile out3\in.txt `
definitionFile tools\ptp\variant27_2addr.target.pdsl `
archName variant27_2addr `
binaryFileToRun out3\out_real_2addr.ptptb `
codeRamBankName code `
ipRegStorageName ip `
finishMnemonicName hlt

На экране появится RUNID.

3. Загрузить stdout по RUNID + показать в шестнадцатеричном виде

✅ .\tools\ptp\Portable.RemoteTasks.Manager.exe -ul 503291 -up "b551163b-6741-4c92-b016-01f99e8a9947" -g $RUNID -r stdout.txt -o out3\run_stdout_calc.txt
✅  Format-Hex -Path .\out3\run_stdout_calc.txt       Здесь будет видно 06 → результат. Эти 3 шага означают, что "калькулятор работает".

---FIBONACCI---

1) ✅ cd C:\Users\Mert\task1
$env:PYTHONPATH = "$PWD\src"

2) Ассемблирование → генерируем .ptptb (обязательно загрузите правильный файл!)

✅ $ASSEMBLE_ID = & .\tools\ptp\Portable.RemoteTasks.Manager.exe `
-ul 503291 -up "b551163b-6741-4c92-b016-01f99e8a9947" `
-id -s Assemble -w `
asmListing out3\fib_variant27_2addr.asm `
definitionFile tools\ptp\variant27_2addr.target.pdsl `
archName variant27_2addr

$ASSEMBLE_ID

3) ✅ & .\tools\ptp\Portable.RemoteTasks.Manager.exe `
  -ul 503291 -up "b551163b-6741-4c92-b016-01f99e8a9947" `
  -g $ASSEMBLE_ID -r out.ptptb -o out3\fib_variant27_2addr.ptptb
dir out3\fib_variant27_2addr.ptptb

4)✅ $n = Read-Host "введите n (например, 5)"
"$n`n" | Set-Content -Encoding ascii out3\in.txt
Get-Content out3\in.txt

5) Запустить программу (ExecuteBinaryWithInput) и получить RUNID

✅ PS C:\Users\Mert\task1> $RUNID = & .\tools\ptp\Portable.RemoteTasks.Manager.exe `
   -ul 503291 -up "b551163b-6741-4c92-b016-01f99e8a9947" `
   -id -s ExecuteBinaryWithInput -w `
   stdinRegStName rin `
   stdoutRegStName rout `
   inputFile out3\in.txt `
   definitionFile tools\ptp\variant27_2addr.target.pdsl `
   archName variant27_2addr `
   binaryFileToRun out3\fib_variant27_2addr.ptptb `
   codeRamBankName code `
   ipRegStorageName ip `
   finishMnemonicName hlt

$RUNID

6) Загрузить stdout и показать результат на экране

 ✅ $RUNID

& .\tools\ptp\Portable.RemoteTasks.Manager.exe `
  -ul 503291 -up "b551163b-6741-4c92-b016-01f99e8a9947" `
  -g $RUNID -r stdout.txt -o out3\fib_stdout.txt
Get-Content out3\fib_stdout.txt | Out-Host




