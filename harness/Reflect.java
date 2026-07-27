import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.junit.jupiter.api.Assertions.fail;

import java.lang.reflect.Constructor;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.lang.reflect.Modifier;
import java.net.URL;
import java.net.URLClassLoader;
import java.util.HashMap;
import java.util.Map;

/**
 * Shared reflective harness for the class/method-based bridge labs
 * (09+). Loads classes from an {@link ExamRunner}'s compile output via
 * a URLClassLoader — deliberately independent of the grader's own
 * classpath — and invokes members reflectively with novice-readable
 * failures. Tolerates both dialects (static methods in named classes,
 * instance methods in implicit classes) and any member visibility.
 *
 * <p>Classes that reference each other (e.g. a Course holding
 * Students) must be compiled TOGETHER: use the
 * {@code new ExamRunner(main, companions...)} constructor so every
 * submission file lands in the same compile.
 */
public final class Reflect {

    private final ExamRunner runner;
    private final String file;
    private ClassLoader loader;
    private final Map<String, Class<?>> cache = new HashMap<>();

    public Reflect(ExamRunner runner, String file) {
        this.runner = runner;
        this.file = file;
    }

    /** The submission compiled cleanly (fail with javac output otherwise). */
    public void assertCompiled() {
        assertTrue(runner.compiledOk(),
                () -> file + " did not compile. The compiler says:\n"
                        + runner.compileError());
    }

    public Class<?> load(String className) {
        assertCompiled();
        return cache.computeIfAbsent(className, name -> {
            try {
                if (loader == null) {
                    loader = new URLClassLoader(
                            new URL[] {runner.classesDir().toUri().toURL()});
                }
                return loader.loadClass(name);
            } catch (Exception e) {
                fail("Could not find the class " + name + " — make sure you "
                        + "submitted it with exactly that name.");
                return null;
            }
        });
    }

    /** new className(args...) using the declared constructor matching sig. */
    public Object construct(String className, Class<?>[] sig, Object... args) {
        Class<?> cls = load(className);
        try {
            Constructor<?> c = cls.getDeclaredConstructor(sig);
            c.setAccessible(true);
            return c.newInstance(args);
        } catch (NoSuchMethodException e) {
            fail(className + " needs a constructor with parameters "
                    + sigNames(sig) + " — check the spec.");
        } catch (InvocationTargetException e) {
            fail("Constructing " + className + " threw " + e.getCause());
        } catch (ReflectiveOperationException e) {
            fail("Could not construct " + className + ": " + e);
        }
        return null;
    }

    /** Call a (possibly static/private) method on target (null = static). */
    public Object call(String className, Object target, String method,
                       Class<?>[] sig, Object... args) {
        Class<?> cls = load(className);
        Method m = null;
        try {
            m = findMethod(cls, method, sig);
        } catch (NoSuchMethodException e) {
            fail(className + "." + method + sigNames(sig) + " not found — make "
                    + "sure the method exists with exactly that name and those "
                    + "parameter types.");
        }
        try {
            m.setAccessible(true);
            Object self = target;
            if (self == null && !Modifier.isStatic(m.getModifiers())) {
                Constructor<?> c = cls.getDeclaredConstructor();
                c.setAccessible(true);
                self = c.newInstance();
            }
            return m.invoke(self, args);
        } catch (InvocationTargetException e) {
            fail(className + "." + method + "() threw " + e.getCause()
                    + " — make sure it handles the tested input.");
        } catch (ReflectiveOperationException e) {
            fail("Could not call " + className + "." + method + "(): " + e);
        }
        return null;
    }

    /** A throwing call: returns the Throwable the method threw (or null). */
    public Throwable callExpectingThrow(String className, Object target,
                                        String method, Class<?>[] sig,
                                        Object... args) {
        Class<?> cls = load(className);
        try {
            Method m = findMethod(cls, method, sig);
            m.setAccessible(true);
            m.invoke(target, args);
            return null;
        } catch (InvocationTargetException e) {
            return e.getCause();
        } catch (ReflectiveOperationException e) {
            fail("Could not call " + className + "." + method + "(): " + e);
            return null;
        }
    }

    private static Method findMethod(Class<?> cls, String name, Class<?>[] sig)
            throws NoSuchMethodException {
        for (Class<?> c = cls; c != null; c = c.getSuperclass()) {
            try {
                return c.getDeclaredMethod(name, sig);
            } catch (NoSuchMethodException ignored) {
                // keep walking up (inherited methods count)
            }
        }
        throw new NoSuchMethodException(name);
    }

    private static String sigNames(Class<?>[] sig) {
        StringBuilder b = new StringBuilder("(");
        for (int i = 0; i < sig.length; i++) {
            b.append(i > 0 ? ", " : "").append(sig[i].getSimpleName());
        }
        return b.append(')').toString();
    }
}
