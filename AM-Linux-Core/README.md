# Arianna Method Linux Kernel

**Arianna Method Linux Kernel (AMLK)** is a deliberately minimal operating nucleus engineered from Alpine sources to provide a deterministic base for AI workloads.

The kernel is configured to load with a small initramfs derived from Alpine's minirootfs, reducing boot complexity to (O(1)) relative to module count.

OverlayFS support enables layered filesystems, modeled as a union (U = R \cup W) where read-only and writable layers intersect for efficient state changes.

Ext4 remains the default persistent store; its journaling function (J(t)) approximates a bounded integral ensuring data integrity under power loss events.

Namespaces form disjoint sets (N_i) partitioning process views of system resources, allowing safe multitenancy without cross-contamination.

Cgroup hierarchies create a tree (T) with resource limits as edge weights, facilitating precise control over CPU and memory distribution.

Python 3.11+ is included for scriptability, and its virtual environment tool venv allows isolation comparable to constructing subspaces within a vector space.

Node.js 18+ complements Python, providing asynchronous I/O modeled as a non-blocking function (f: E \to E) where events map to themselves after processing.

Bash, curl, and nano compose the minimal interactive toolkit; each utility occupies a vertex in a dependency graph ensuring accessibility without bloat.

The CLI terminal shipped in `letsgo.py` demonstrates logging and echo capabilities, acting as a proof of concept for higher-order reasoning modules.

When the host kernel supports eBPF and the Python `bcc` bindings are present,
`letsgo.py` sources CPU, disk and network statistics from a small
`kernel_metrics` module.  On systems lacking eBPF support these commands
silently fall back to parsing files under `/proc`, ensuring basic monitoring
still functions.

Logs are stored in `/arianna_core/log` and each entry is timestamped, forming a sequence ((t_i, m_i)) representing chronological states of dialogue.

The build script uses curl to fetch kernel and rootfs sources, then applies a configuration where required options satisfy predicates for ext4, overlay, and isolation features.

During compilation, the command `make -j n` leverages parallelism, aligning with the formula for speedup (S = \frac{T_1}{T_n}) from Amdahl's law.

Initramfs assembly employs cpio and gzip, treating the filesystem as a multiset to be serialized into a compressed stream (C) ready for kernel consumption.

The final image concatenates bzImage and the compressed initramfs, yielding a flat artifact optimized for QEMU execution and network deployment.

QEMU invocation sets the console to ttyS0 and disables graphical output, thus the system behaves like a linear state machine observable via standard I/O.

Verifications inside the emulator include `python3 --version` and `node --version`; successful output serves as an identity proof for runtime availability.

The project directory conforms to a strict lattice: `kernel` for build artifacts, `core` for modules, `cmd` for executables, `usr/bin` for runtime tools, and `log` for reasoning traces.

Each component is annotated with comments using the `//:` motif, a notation indicating future extensibility in the style of a category morphism awaiting composition.

AMLK is lightweight enough to embed within messaging clients like Telegram, allowing AI agents to inhabit user devices with minimal computational overhead.

---

## Hardware Requirements

The kernel and userland target generic x86_64 CPUs. GPU drivers and libraries are omitted, so the system runs entirely on CPU hardware.

---

## Continuous Integration

The CI pipeline builds the kernel and boots it in QEMU using only CPU resources. GPU devices and drivers are absent, and QEMU is invoked with software acceleration so the workflow succeeds on generic CPU-only runners.

---

## Building

First build the trimmed package manager:

```bash
./build/build_apk_tools.sh
Then assemble the kernel and userland:
./build/build_ariannacore.sh [--with-python] [--clean] [--test-qemu]

The second script fetches kernel sources, stages arianna_core_root built from the Alpine lineage, and emits a flat image. The optional flags expand the userland, clean previous artifacts or run a QEMU smoke test.

⸻

## Linting

Run static analysis before pushing changes (install flake8, flake8-pyproject, and black if missing):
The second script fetches kernel sources, stages arianna_core_root built from the Alpine lineage, and emits a flat image. The optional flags expand the userland, clean previous artifacts or run a QEMU smoke test.

⸻

Linting

Run static analysis before pushing changes (install flake8, flake8-pyproject, and black if missing):
./run-tests.sh
This script executes flake8 and black --check followed by the test suite. To run the linters directly:
flake8 .
black --check .

Lineage utilities

The apk-tools directory carries a patched apk built by build_apk_tools.sh, enabling package installs without heavy dependencies.

⸻

Checksum verification

For reproducibility the build script verifies downloads against known SHA256 sums using:
echo "<sha256>  <file>" | sha256sum -c -

The current release embeds the following official values:
	•	linux-6.6.4.tar.gz: 43d77b1816942ed010ac5ded8deb8360f0ae9cca3642dc7185898dab31d21396
	•	arianna_core_root-3.19.8-x86_64.tar.gz: 48230b61c9e22523413e3b90b2287469da1d335a11856e801495a896fd955922

If a checksum mismatch occurs the build aborts immediately.

⸻

Vendored components

The apk-tools/ directory carries a pared-down copy of apk-tools.
build/build_apk_tools.sh compiles this tree and build/build_ariannacore.sh stages the resulting apk binary into arianna_core_root to install packages without network access.

Keeping this component local aligns with the CPU-only, minimalistic design:
the build remains self-contained, avoids heavy dependencies and produces a small userland that boots on generic hardware.

⸻

Running in QEMU

A minimal invocation uses the arianna-core.img created during the build. QEMU can operate in headless mode:
qemu-system-x86_64 -kernel build/kernel/linux-*/arch/x86/boot/bzImage -initrd build/arianna.initramfs.gz -append "console=ttyS0" -nographic

For repeatable experiments, keep memory to 512M and disable reboot so that the exit status bubbles up to the host. The console is directed to ttyS0, allowing simple piping to tmux panes or log files.

When --test-qemu is supplied to the build script, the above sequence is executed automatically; artifacts remain under the boot/ directory for manual launches later on.

⸻

Future Interfaces

A Telegram bridge is planned through a small bot that proxies chat messages to letsgo.py. The bot will authenticate via API token and map each chat to a session log, enabling asynchronous reasoning threads.

A web UI may follow, exposing the same terminal over WebSockets. The intent is to treat HTTP as a transport layer while preserving the conversational core. SSL termination and rate limiting will rely on existing libraries and can run in user space atop the initramfs.

Other interfaces—serial TTYs, named pipes or custom RPC schemes—remain feasible because the terminal operates in standard I/O space, reducing coupling to any specific frontend.

⸻

letsgo.py

The terminal is invoked after login and serves as the primary shell for Arianna Core. Each session creates a fresh log in /arianna_core/log/, stamped with UTC time, ensuring chronological reconstruction of interactions. A max_log_files option in ~/.letsgo/config limits how many of these log files are kept on disk.

Command history is persisted to /arianna_core/log/history. Existing entries load at startup and are written back on exit. Tab completion, powered by readline, suggests built-in verbs like /status, /time, /run, /summarize, /search, /color, and /help.

A /status command reports CPU core count, raw uptime seconds read from /proc/uptime, and the current host IP. This offers an at-a-glance check that the minimal environment is healthy.

The /summarize command searches across logs with optional regular expressions and prints the last five matches; adding --history switches the search to the command history. /search <pattern> prints every history line matching the given regex.

For quick information retrieval /time prints the current UTC timestamp, while /run <cmd> executes a shell command and returns its output. A /help command lists the available verbs. Use /color on|off to toggle colored output.

By default any unrecognised input is echoed back, but the structure is prepared for more advanced NLP pipelines. Hooks can intercept the text and dispatch it to remote models, feeding results back through the same interface.

Logging uses the //: motif in comments and writes both user prompts and letsgo responses. Each line is timestamped with ISO-8601 precision, building a dataset suitable for replay or training.

Because letsgo.py resides in the repository root, the cmd directory only carries thin launchers. startup.py triggers the terminal on boot, while monitor.sh tails log files for real-time inspection.

The design keeps dependencies minimal. The script relies only on the Python standard library and can run inside the initramfs without additional packages unless --with-python is chosen.

As the project evolves, the terminal is expected to grow into a pluggable orchestrator capable of spawning subprocesses, managing asynchronous tasks and negotiating resources with the kernel via cgroups.

When invoked through the Python bridge, `letsgo.py` now runs inside its own cgroup. Resource ceilings can be tuned by setting environment variables before launch:

* `LETSGO_CPU_LIMIT` writes directly to `cpu.max` and controls the CPU quota, e.g. `50000 100000` for 50% of one core.
* `LETSGO_MEMORY_LIMIT` writes to `memory.max` and caps the memory footprint, e.g. `512M`.

```
LETSGO_CPU_LIMIT="50000 100000" LETSGO_MEMORY_LIMIT=512M python3 main.py
```

The limits are applied after the subprocess starts; absent variables leave the cgroup unmodified.

⸻

Architecture

The kernel forms a deterministic foundation carved from Alpine sources. Every configuration option is scrutinized so the space of parameters (K = {k_1, k_2, …, k_n}) collapses to a minimal subset that still spans ext4, OverlayFS, and namespace features.

The build pipeline orchestrates source retrieval and configuration as if solving simultaneous equations. Each Make rule enforces constraints for ext4, OverlayFS, and cgroups, and parallel compilation realizes the speedup (S = T_1/T_n).

Boot logic assembles bzImage and a compressed initramfs into a linear product (B = b \cdot r). This concatenation behaves like a monoid multiplication where associativity guarantees reproducible startup sequences across machines.

File persistence relies on ext4 journaling. The journal approximates an integral (J(t) = \int_0^t \dot{d}(\tau) d\tau), bounding data loss even when power is cut mid write.

OverlayFS introduces a writable layer (W) atop a read-only base (R), yielding an effective state (S = R \cup W). The union is resolved at lookup time, so modifications scale with O(1) regardless of history depth.

Namespaces partition the universe of processes into disjoint sets (N_i). Each process perceives only its assigned set, echoing Leibniz’s monads in computational form.

Cgroups enforce resource bounds through a tree (T) whose edges carry weights (w_e). The sum of leaf allocations (\sum w_e) never exceeds the root capacity, keeping runaway tasks in check.

Userland emerges from arianna_core_root, a trimmed Alpine derivative. Think of it as the base vector (u_0) in a high-dimensional space where each package installation performs a vector addition (u_{n+1} = u_n + p).

The terminal letsgo.py now hosts all core commands directly, abandoning plugins for a monolith that reduces indirection. Its interface targets the human eye with concise prompts yet invites scripting through deterministic outputs.

Interaction unfolds through an asynchronous loop (L), mapping each input (i_t) to a response (o_t). The mapping is a pure function except for deliberate side effects like logging.

Logs accumulate as a sequence (L = [(t_0, m_0), (t_1, m_1), …]). This ordered set enables reconstruction of conversations and supports algorithms that treat time as a first-class axis.

Summarization and regex search act as projection operators (\pi: L \rightarrow L’), distilling salient points without destroying provenance. History retrieval behaves like a bounded inverse, recovering the last (n) elements of (L).

Color output toggles between states (C_{on}) and (C_{off}). The flag is stored in memory, and switching corresponds to a simple Boolean complement (C’ = \neg C).

The /status command samples CPU count, uptime, and network address. It forms a vector (s = (c, u, a)) that approximates the machine’s physical posture in real time.

The freshly integrated /ping command provides a liveness probe. Conceptually it models an impulse response where (f(t) = \delta(t)) and the echo pong verifies that the terminal loop is intact.

Command execution leverages asyncio.create_subprocess_shell, achieving concurrency. The speedup follows Amdahl’s law (S = \frac{T_1}{T_n}), reminding users that parallelism has theoretical limits.

Minimalism is the guiding philosophy. By shedding superfluous layers the system mirrors Occam’s razor, asserting that the simplest explanation—or kernel—should be preferred until complexity becomes unavoidable.

Security arises from this austerity. With fewer packages, the attack surface approximates a measure-zero subset in the wider space of Linux distributions.

Despite its monolithic posture, the design remains extensible. Future bridges to chat platforms or web consoles can attach as morphisms without mutating the core algebra.

Ultimately the architecture invites self-reflection. When the terminal inspects its own logs, it computes a recursion (x_{n+1} = f(x_n)), hinting at systems that learn and adapt through iterative self-observation.

⸻

License

This project is licensed under the GNU General Public License v3.0.
