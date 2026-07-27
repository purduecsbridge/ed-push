import static org.junit.jupiter.api.Assertions.assertEquals;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Tag;
import org.junit.jupiter.api.Test;

public class GreeterTest {

    @Test
    @DisplayName("Greets by name")
    @Tag("score:2")
    void greetsByName() {
        assertEquals("Hello, Ada!", new Greeter().greet("Ada"));
    }

    @Test
    @DisplayName("Works for any name")
    @Tag("score:1")
    void worksForAnyName() {
        assertEquals("Hello, Bo!", new Greeter().greet("Bo"));
    }
}
