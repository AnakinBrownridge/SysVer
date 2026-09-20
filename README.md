# SysVer

SysVer is a cross-platform Python command-line utility that displays detailed information about the computer it is running on. It is designed for Windows, macOS, and Linux and presents the results in a readable terminal format or as machine-readable JSON.

## What it reports

SysVer collects and displays:

- Operating system and kernel version
- System architecture
- Processor model
- Physical and logical CPU counts
- CPU frequency, when available
- Load average, on platforms that support it
- Python version
- Current user and display name, when available
- Hostname
- Non-loopback IP addresses
- System uptime and calculated boot time
- Memory totals, available memory, used memory, and usage percentage when available
- Disk capacity and free space for the primary system volume

The script uses platform-specific fallbacks where necessary. For example, it can query `/proc` on Linux, `sysctl` on macOS, and Windows tools such as WMIC, `net user`, and PowerShell when available.

## Features

- Cross-platform support for Windows, macOS, and Linux
- Enhanced hardware and memory information through `psutil`
- Optional colored terminal output through `colorama`
- Processor-brand detection through `py-cpuinfo`
- Box or two-column table output
- JSON output for scripts and automation
- Graceful fallbacks when a platform-specific command or data source is unavailable

## Screenshots

![SysVer screenshot 1](https://github.com/AnakinBrownridge/SysVer/blob/main/Screenshot%202026-09-20%20163121.png?raw=true)

![SysVer screenshot 2](https://github.com/AnakinBrownridge/SysVer/blob/main/Screenshot%202026-09-20%20163244.png?raw=true)

## Requirements

- Python 3.9 is recommended (as it was developed on that version)
- Windows, macOS, or Linux

The project dependencies are listed in [`requirements.txt`](requirements.txt):

- `psutil` — CPU, memory, and uptime information
- `colorama` — colored terminal output
- `py-cpuinfo` — processor-brand detection

Install all dependencies with:

```bash
python -m pip install -r requirements.txt
```

On some systems, use `python3` instead:

```bash
python3 -m pip install -r requirements.txt
```

The script handles unavailable optional system data gracefully, so some values may still be reported as `Unknown` if the operating system does not expose them.

## Usage

From the repository root, run:

```bash
python SysVer/SysVer.py
```

On some systems, use `python3` instead:

```bash
python3 SysVer/SysVer.py
```

### Command-line options

```text
--json          Output the collected information as formatted JSON
--format       Select the terminal format: box or table
--no-color      Disable ANSI color output
--verbose       Enable the verbose option (reserved for additional debug output)
```

### Examples

Default box output:

```bash
python SysVer/SysVer.py
```

Table output without color:

```bash
python SysVer/SysVer.py --format table --no-color
```

JSON output for automation:

```bash
python SysVer/SysVer.py --json
```

Save JSON output to a file:

```bash
python SysVer/SysVer.py --json > system-info.json
```

## How it works

The main program gathers data through a set of small platform-aware functions:

1. `get_sys_info()` assembles the complete system-information dictionary.
2. Operating-system details come from Python's `platform` module.
3. CPU and memory data use `psutil` when installed, with standard-library fallbacks where possible.
4. Disk usage is read using `shutil.disk_usage()` for the system drive or root volume.
5. Network addresses are discovered using hostname resolution, with a local socket fallback.
6. Uptime is read from `psutil`, Linux `/proc/uptime`, or Windows boot-time commands.
7. The result is rendered as a box, table, or JSON document.

The terminal is cleared before formatted output is printed. JSON output is printed directly without the formatted terminal layout.

## Project structure

```text
.
├── LICENSE
├── requirements.txt
├── SysVer.slnx
└── SysVer
    ├── SysVer.py
    └── SysVer.pyproj
```

`SysVer.py` contains the complete utility, `requirements.txt` lists its Python dependencies, and `SysVer.pyproj` provides Visual Studio Python project configuration.

## Limitations and notes

- Some values depend on the operating system and available permissions.
- CPU frequency, load average, memory statistics, and processor model may show `Unknown` when the platform does not expose them or a dependency cannot provide them.
- IP discovery reports non-loopback addresses and may not include every network interface.
- The primary disk volume is inspected rather than every mounted volume.
- Windows-specific probes rely on commands that may be missing or deprecated on newer installations. SysVer falls back gracefully when they cannot be run.
- The `--verbose` option is accepted by the command-line interface but currently does not add extra output.

## License

See [LICENSE](LICENSE) for the license that applies to this project.
