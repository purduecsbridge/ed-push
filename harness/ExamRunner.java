import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.OutputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Map;
import java.util.concurrent.TimeUnit;

/**
 * Mid2 edition of the exam harness (Modes A and B). Same design as the proven
 * Mid1 {@code _harness/ExamRunner}: compile the submission ONCE, then launch a
 * fresh JVM per test case (which is what makes implicit {@code void main()} /
 * classic {@code static main(String[])} and {@code IO} / {@code Scanner} all
 * grade alike, and erases all static state between cases).
 *
 * <p><b>New for Mid2 (Mode B, file challenges):</b> every {@link #run} gets its
 * own fresh <b>working directory</b>. Input files can be staged into it before
 * the run ({@code run(stdin, Map.of("sales.txt", "..."))}), and files the
 * program wrote can be read back from it afterward
 * ({@link Result#fileExists}, {@link Result#fileLines},
 * {@link Result#fileValue}). A missing-file test simply stages nothing.
 *
 * <p><b>Decided observable for the missing-file behavior</b> (was an open
 * question): assert all three of (1) the message on stdout, (2) the output
 * file does NOT exist, (3) {@code exitCode == 0}. A submission that lets the
 * exception escape fails (2 is untouched but 3 is nonzero and the trace is on
 * stderr); one that catches but still opens the writer fails (2).
 *
 * <p>Mode A usage is unchanged from Mid1: {@code runner.run(stdin)} and
 * assert on {@link Result#value}.
 */
public final class ExamRunner {

    private static final long TIMEOUT_SECONDS = 10;

    private final Path workDir;      // compiled classes live here
    private final String mainClass;
    private final boolean compiled;
    private final String compileError;

    public ExamRunner(String sourcePath) {
        this(sourcePath, new String[0]);
    }

    /**
     * Compile {@code sourcePath} together with {@code companions} (other
     * submission files it references) into one fresh directory.
     */
    public ExamRunner(String sourcePath, String... companions) {
        Path src = Path.of(sourcePath).toAbsolutePath();
        String fileName = src.getFileName().toString();
        if (!fileName.endsWith(".java")) {
            throw new IllegalArgumentException("expected a .java file, got: " + sourcePath);
        }
        this.mainClass = fileName.substring(0, fileName.length() - ".java".length());

        Path dir = null;
        boolean ok = false;
        String err = "";
        try {
            dir = Files.createTempDirectory("examrun-" + mainClass + "-");
            var cmd = new java.util.ArrayList<String>();
            cmd.add("javac");
            cmd.add("-d");
            cmd.add(dir.toString());
            Path copied = dir.resolve(fileName);
            Files.copy(src, copied);
            cmd.add(copied.toString());
            for (String companion : companions) {
                Path cSrc = Path.of(companion).toAbsolutePath();
                if (Files.exists(cSrc)) {
                    Path cCopy = dir.resolve(cSrc.getFileName().toString());
                    Files.copy(cSrc, cCopy);
                    cmd.add(cCopy.toString());
                }
            }

            Process javac = new ProcessBuilder(cmd)
                    .redirectErrorStream(true)
                    .start();
            String out = readAll(javac.getInputStream());
            boolean done = javac.waitFor(TIMEOUT_SECONDS, TimeUnit.SECONDS);
            if (!done) {
                javac.destroyForcibly();
                err = "javac timed out";
            } else {
                ok = javac.exitValue() == 0;
                if (!ok) err = out;
            }
        } catch (IOException | InterruptedException e) {
            err = String.valueOf(e);
        }
        this.workDir = dir;
        this.compiled = ok;
        this.compileError = err;
    }


    /** Directory holding the compiled classes (for reflective loading). */
    public java.nio.file.Path classesDir() {
        return workDir;
    }

    public boolean compiledOk() {
        return compiled;
    }

    public String compileError() {
        return compileError;
    }

    /** Mode A: run with stdin only; the run directory starts empty. */
    public Result run(String stdin) {
        return run(stdin, Map.of());
    }

    /**
     * Mode B: stage {@code files} (name -> full contents) into a fresh run
     * directory, run the program with that directory as its working directory,
     * and expose whatever it printed and wrote.
     */
    public Result run(String stdin, Map<String, String> files) {
        if (!compiled) {
            return new Result("", compileError, -1, false, false, null);
        }
        try {
            Path runDir = Files.createTempDirectory("examrun-case-");
            for (Map.Entry<String, String> f : files.entrySet()) {
                Files.writeString(runDir.resolve(f.getKey()), f.getValue());
            }
            Process p = new ProcessBuilder("java", "-cp", workDir.toString(), mainClass)
                    .directory(runDir.toFile())
                    .start();
            try (OutputStream os = p.getOutputStream()) {
                os.write(stdin.getBytes());
            }
            String out = readAll(p.getInputStream());
            String errOut = readAll(p.getErrorStream());
            boolean done = p.waitFor(TIMEOUT_SECONDS, TimeUnit.SECONDS);
            if (!done) {
                p.destroyForcibly();
                return new Result(out, errOut, -1, true, true, runDir);
            }
            return new Result(out, errOut, p.exitValue(), false, true, runDir);
        } catch (IOException | InterruptedException e) {
            return new Result("", String.valueOf(e), -1, false, true, null);
        }
    }

    private static String readAll(java.io.InputStream in) throws IOException {
        ByteArrayOutputStream buf = new ByteArrayOutputStream();
        in.transferTo(buf);
        return buf.toString();
    }

    /** Captured outcome of one run: stdout, stderr, exit code, and the run directory's files. */
    public static final class Result {
        public final String stdout;
        public final String stderr;
        public final int exitCode;
        public final boolean timedOut;
        public final boolean compiled;
        private final Path runDir;
        public final List<String> lines;

        Result(String stdout, String stderr, int exitCode, boolean timedOut,
               boolean compiled, Path runDir) {
            this.stdout = stdout;
            this.stderr = stderr;
            this.exitCode = exitCode;
            this.timedOut = timedOut;
            this.compiled = compiled;
            this.runDir = runDir;
            this.lines = stdout.isEmpty() ? List.of() : Arrays.asList(stdout.split("\n", -1));
        }

        /** Value printed after a unique label on STDOUT (prompt-tolerant, as in Mid1). */
        public String value(String label) {
            return valueIn(stdout, label);
        }

        public boolean hasLine(String expected) {
            for (String ln : lines) {
                if (ln.equals(expected) || ln.endsWith(expected)) return true;
            }
            return false;
        }

        // ---- Mode B: the run directory's files ----

        /** True if the program's run directory now contains {@code name}. */
        public boolean fileExists(String name) {
            return runDir != null && Files.exists(runDir.resolve(name));
        }

        /** The lines of a file the program wrote; empty list if absent. */
        public List<String> fileLines(String name) {
            try {
                if (!fileExists(name)) return List.of();
                return Files.readAllLines(runDir.resolve(name));
            } catch (IOException e) {
                return List.of();
            }
        }

        /** Value after a unique label inside a written file (line-based, trimmed). */
        public String fileValue(String name, String label) {
            for (String ln : fileLines(name)) {
                int idx = ln.indexOf(label);
                if (idx >= 0) return ln.substring(idx + label.length()).trim();
            }
            return null;
        }

        private static String valueIn(String text, String label) {
            int idx = text.indexOf(label);
            if (idx < 0) return null;
            int from = idx + label.length();
            int nl = text.indexOf('\n', from);
            String slice = (nl < 0) ? text.substring(from) : text.substring(from, nl);
            return slice.trim();
        }
    }
}
