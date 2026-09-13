// StrawKnight launcher.
//
// A double-clickable front door for the container, for Windows and Linux. It
// does exactly what the two start scripts do; it exists because a script on
// Windows means a right-click and a word about execution policy, and a
// download that needs an explanation is a download people abandon.
//
// IT DOES NOT CONTAIN THE PRODUCT. The payload is a twelve gigabyte Linux
// image that needs KVM, so there is no version of this that runs without
// Docker. What this binary saves is the setup, not the dependency, and it says
// so rather than pretending otherwise.
//
// THE WINDOWS PART IS THE WHOLE POINT. There, the container runs inside the
// WSL2 machine, so KVM has to work inside a VM. That needs
// nestedVirtualization=true in a file nothing prompts anyone to create, and
// even then /dev/kvm arrives owned by root with mode 600 while the emulator
// runs as an ordinary user. Both were measured, and both are handled here,
// because the failure they produce looks like a broken image rather than a
// missing setting.
package main

import (
	"bufio"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
)

const (
	image     = "ghcr.io/junkerderprovinz/strawknight:latest"
	container = "StrawKnight"
	port      = "3001"
	adbPort   = "5555"
)

// Colour only where it is understood. Windows Terminal and PowerShell 7 read
// ANSI, the old conhost does not, and a prompt full of escape codes is worse
// than a plain one.
var useColour = runtime.GOOS != "windows" || os.Getenv("WT_SESSION") != ""

func paint(code, s string) string {
	if !useColour {
		return s
	}
	return "\033[" + code + "m" + s + "\033[0m"
}

func step(s string) { fmt.Println("\n" + paint("36", "=== "+s+" ===")) }
func say(s string)  { fmt.Println("  " + s) }
func ok(s string)   { fmt.Println("  " + paint("32", s)) }
func bad(s string)  { fmt.Println("  " + paint("31", s)) }

// stop prints, waits for a keypress and exits. Without the wait a
// double-clicked binary closes its window on the error message, which is the
// one moment somebody needed to read it.
func stop(code int) {
	if runtime.GOOS == "windows" {
		fmt.Print("\n  Press Enter to close. ")
		bufio.NewReader(os.Stdin).ReadString('\n')
	}
	os.Exit(code)
}

func run(name string, args ...string) (string, error) {
	out, err := exec.Command(name, args...).CombinedOutput()
	return strings.TrimSpace(string(out)), err
}

// runLoud streams to the terminal instead of collecting output. Used for the
// pull, which takes minutes and is unbearable without progress.
func runLoud(name string, args ...string) error {
	cmd := exec.Command(name, args...)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	return cmd.Run()
}

func ask(q string) bool {
	fmt.Print("  " + q + " [y/N] ")
	line, _ := bufio.NewReader(os.Stdin).ReadString('\n')
	line = strings.ToLower(strings.TrimSpace(line))
	return line == "y" || line == "j" || line == "yes" || line == "ja"
}

func dockerPath() string {
	if p, err := exec.LookPath("docker"); err == nil {
		return p
	}
	// Docker Desktop only puts itself on PATH for sessions started after the
	// install, so the very first run after installing would otherwise fail on
	// a program that is sitting right there.
	if runtime.GOOS == "windows" {
		dir := `C:\Program Files\Docker\Docker\resources\bin`
		p := filepath.Join(dir, "docker.exe")
		if _, err := os.Stat(p); err == nil {
			// And the directory goes on PATH, not just the one binary. docker
			// shells out to docker-credential-desktop by NAME when it talks to
			// a registry, so calling docker by its full path gets as far as the
			// pull and then fails on a helper sitting in the same folder.
			os.Setenv("PATH", dir+string(os.PathListSeparator)+os.Getenv("PATH"))
			return p
		}
	}
	return ""
}

var docker string

func checkDocker() {
	step("Docker")
	docker = dockerPath()
	if docker == "" {
		bad("Docker is not installed.")
		if runtime.GOOS == "windows" {
			say("Install it with:  winget install --id Docker.DockerDesktop")
		} else {
			say("https://docs.docker.com/engine/install/")
		}
		stop(1)
	}
	if _, err := run(docker, "version", "--format", "{{.Server.Version}}"); err != nil {
		bad("The Docker engine does not answer.")
		if runtime.GOOS == "windows" {
			say("Start Docker Desktop, wait for the whale to stop moving, and try again.")
		} else {
			say("Is the service running, and are you in the docker group?")
		}
		stop(1)
	}
	ok("engine is up")
}

func checkWindows() {
	step("Nested virtualisation")
	home, _ := os.UserHomeDir()
	cfg := filepath.Join(home, ".wslconfig")
	body, _ := os.ReadFile(cfg)
	if strings.Contains(strings.ToLower(string(body)), "nestedvirtualization=true") {
		ok("nestedVirtualization=true is set in " + cfg)
	} else {
		bad("nestedVirtualization is missing from " + cfg)
		say("Without it the WSL machine has no /dev/kvm and the emulator will not start.")
		if !ask("Write it now and restart WSL?") {
			say("Stopped.")
			stop(1)
		}
		if len(body) > 0 {
			_ = os.WriteFile(cfg+".bak", body, 0o644)
			say("backup: " + cfg + ".bak")
		}
		old := string(body)
		var neu string
		if strings.Contains(strings.ToLower(old), "[wsl2]") {
			// Insert directly under the existing section header rather than
			// appending: a key after a later section header belongs to that
			// section and is silently ignored.
			i := strings.Index(strings.ToLower(old), "[wsl2]")
			neu = old[:i+6] + "\nnestedVirtualization=true" + old[i+6:]
		} else {
			neu = "[wsl2]\nnestedVirtualization=true\n\n" + old
		}
		if err := os.WriteFile(cfg, []byte(neu), 0o644); err != nil {
			bad("could not write " + cfg + ": " + err.Error())
			stop(1)
		}
		ok("written")
		say("Restarting WSL. This closes running containers.")
		_, _ = run("wsl.exe", "--shutdown")
	}

	step("KVM")
	// TWO THINGS HAVE TO HAPPEN, and neither is done for us.
	//
	// First, the module is not loaded when the WSL machine boots, so /dev/kvm
	// simply does not exist, nested virtualisation or not. modprobe registers
	// the misc device and the node appears.
	//
	// Second, the node then belongs to root with mode 600, while the emulator
	// inside the container runs as an ordinary user. Left alone, the container
	// starts, the desktop serves, and the emulator prints a page about
	// groupadd and udev rules that describes a Linux host and does not apply
	// here.
	//
	// Both are repeated on every run on purpose: the WSL machine is rebuilt
	// whenever Docker Desktop restarts, and everything done in it is gone.
	_, _ = run("wsl.exe", "-d", "docker-desktop", "-e", "sh", "-c",
		"modprobe kvm_intel 2>/dev/null || modprobe kvm_amd 2>/dev/null; chmod 666 /dev/kvm 2>/dev/null")

	mode, _ := run("wsl.exe", "-d", "docker-desktop", "-e", "sh", "-c", "ls -l /dev/kvm 2>&1")
	switch {
	case strings.Contains(mode, "crw-rw-rw-"):
		ok("/dev/kvm is there and open for the container")
	case strings.Contains(mode, "No such file"):
		bad("/dev/kvm is missing inside the WSL machine.")
		say("The usual causes: virtualisation is off in the BIOS, or Windows is itself")
		say("running in a VM that does not pass VT-x through.")
		stop(1)
	default:
		bad("could not open /dev/kvm for the container; the emulator will probably not start")
		say(mode)
	}
}

func checkLinux() {
	step("KVM")
	if _, err := os.Stat("/dev/kvm"); err != nil {
		bad("/dev/kvm is missing.")
		say("Without KVM the emulator will not start. The usual causes:")
		say("  * virtualisation is switched off in the BIOS")
		say("  * this machine is itself a VM without nested virtualisation")
		say("  * the module is not loaded:  sudo modprobe kvm_intel   (or kvm_amd)")
		stop(1)
	}
	// Readable is not the same as present, and the difference decides whether
	// the phone boots. Reported rather than fixed: widening a device node on
	// somebody's own machine is not this program's business.
	if f, err := os.OpenFile("/dev/kvm", os.O_RDWR, 0); err != nil {
		bad("/dev/kvm exists but you cannot open it: " + err.Error())
		say("Usually a missing group:  sudo usermod -aG kvm $USER   then log in again.")
	} else {
		_ = f.Close()
	}
	ok("/dev/kvm is there")
}

func start() {
	step("Image")
	say("About 12 GB the first time. Later starts reuse it.")
	if err := runLoud(docker, "pull", image); err != nil {
		bad("pull failed: " + err.Error())
		stop(1)
	}

	step("Start")
	_, _ = run(docker, "rm", "-f", container)

	args := []string{
		"run", "-d", "--name", container,
		"--device=/dev/kvm",
		"-p", port + ":3001",
		"-p", adbPort + ":5555",
		"-v", "strawknight-config:/config",
		"--shm-size=2gb", "--cpus=4", "--memory=8g",
		"-e", "EMULATOR_GPU=swiftshader_indirect",
		"-e", "EMULATOR_DEVICE=pixel_6",
		"-e", "EMULATOR_RAM=2048",
	}
	if runtime.GOOS == "linux" {
		// Who owns /config has to match who runs the emulator. Get it wrong and
		// the emulator cannot write into its own AVD, and says so as
		// "A snapshot operation is pending", which reads like a corrupt device
		// and is a permission bit.
		args = append(args, "-e", fmt.Sprintf("PUID=%d", os.Getuid()), "-e", fmt.Sprintf("PGID=%d", os.Getgid()))
	}
	args = append(args, image)

	if out, err := run(docker, args...); err != nil {
		bad("could not start the container:")
		say(out)
		stop(1)
	}

	ok("started")
	fmt.Println()
	say("Screen:  https://localhost:" + port + "/    (self-signed, accept it once)")
	say("Deploy:  adb connect localhost:" + adbPort)
	fmt.Println()
	say("The first start creates the device and takes a few minutes.")
	say("Follow it with:  docker logs -f " + container)
	say("Stop it with:    docker stop " + container)
}

func main() {
	fmt.Println(paint("33", "\n  StrawKnight") + "  -  a real Android emulator, in a browser")
	say("This starts the container. It needs Docker; it is not a standalone app.")

	checkDocker()
	switch runtime.GOOS {
	case "windows":
		checkWindows()
	case "linux":
		checkLinux()
	default:
		bad("Only Windows and Linux are handled here.")
		say("On macOS the emulator cannot use KVM at all, so this image does not apply.")
		stop(1)
	}
	start()
	stop(0)
}
