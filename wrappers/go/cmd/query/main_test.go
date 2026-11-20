package main

import (
	"bytes"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"
)

var binary string

// TestMain builds this command once. `go run` is not used: it reports every
// non-zero exit of the program as its own exit status 1.
func TestMain(m *testing.M) {
	dir, err := os.MkdirTemp("", "iso3166-query-")
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	binary = filepath.Join(dir, "query")
	if out, err := exec.Command("go", "build", "-o", binary, ".").CombinedOutput(); err != nil {
		fmt.Fprintf(os.Stderr, "go build: %v\n%s", err, out)
		os.RemoveAll(dir)
		os.Exit(1)
	}
	code := m.Run()
	os.RemoveAll(dir)
	os.Exit(code)
}

// run executes the built command and returns stdout, stderr and the exit code.
func run(t *testing.T, args ...string) (string, string, int) {
	t.Helper()
	cmd := exec.Command(binary, args...)
	var stdout, stderr bytes.Buffer
	cmd.Stdout, cmd.Stderr = &stdout, &stderr
	err := cmd.Run()
	code := 0
	if err != nil {
		ee, ok := err.(*exec.ExitError)
		if !ok {
			t.Fatalf("run %s: %v", binary, err)
		}
		code = ee.ExitCode()
	}
	return stdout.String(), stderr.String(), code
}

func TestBordersTransitivelyBadMaxHopsExitsTwo(t *testing.T) {
	for _, bad := range []string{"abc", "", "1.5", "2x"} {
		out, errOut, code := run(t, "borders_transitively", "US", bad)
		if code != 2 {
			t.Errorf("max_hops %q: exit %d, want 2 (stdout %q)", bad, code, out)
		}
		if out != "" {
			t.Errorf("max_hops %q: printed %q, want nothing", bad, out)
		}
		if !strings.Contains(errOut, "max_hops") {
			t.Errorf("max_hops %q: stderr %q does not name max_hops", bad, errOut)
		}
	}
}

func TestBordersTransitivelyGoodMaxHopsStillWorks(t *testing.T) {
	out, _, code := run(t, "borders_transitively", "US", "1")
	if code != 0 || strings.TrimSpace(out) != `["CA","MX"]` {
		t.Errorf("exit %d, stdout %q", code, out)
	}
}
