import argparse
import datetime
import json
import os
import platform
import re
import shutil
import socket
import subprocess
import sys
import time

try:
    import psutil
except Exception:
    psutil = None

try:
    from colorama import init as _color_init, Fore, Style
    _color_init(autoreset=True)
    COLOR_AVAILABLE = True
except Exception:
    COLOR_AVAILABLE = False

    class Fore:
        BLACK = ""
        RED = ""
        GREEN = ""
        YELLOW = ""
        BLUE = ""
        MAGENTA = ""
        CYAN = ""
        WHITE = ""
        RESET = ""
        BASE03 = ""
        BASE02 = ""
        BASE01 = ""
        BASE00 = ""
        BASE0 = ""
        BASE1 = ""
        BASE2 = ""
        BASE3 = ""
        ORANGE = ""
        VIOLET = ""
        SOLARIZED_BASE03 = ""
        SOLARIZED_BASE02 = ""
        SOLARIZED_BASE01 = ""
        SOLARIZED_BASE00 = ""
        SOLARIZED_BASE0 = ""
        SOLARIZED_BASE1 = ""
        SOLARIZED_BASE2 = ""
        SOLARIZED_BASE3 = ""
        SOLARIZED_YELLOW = ""
        SOLARIZED_ORANGE = ""
        SOLARIZED_RED = ""
        SOLARIZED_MAGENTA = ""
        SOLARIZED_VIOLET = ""
        SOLARIZED_BLUE = ""
        SOLARIZED_CYAN = ""
        SOLARIZED_GREEN = ""

    class Style:
        BRIGHT = ""
        DIM = ""
        RESET_ALL = ""

SOLARIZED = {
    "BASE03": "\033[38;5;234m",
    "BASE02": "\033[38;5;235m",
    "BASE01": "\033[38;5;240m",
    "BASE00": "\033[38;5;241m",
    "BASE0": "\033[38;5;246m",
    "BASE1": "\033[38;5;247m",
    "BASE2": "\033[38;5;254m",
    "BASE3": "\033[38;5;230m",
    "YELLOW": "\033[38;5;136m",
    "ORANGE": "\033[38;5;166m",
    "RED": "\033[38;5;160m",
    "MAGENTA": "\033[38;5;168m",
    "VIOLET": "\033[38;5;61m",
    "BLUE": "\033[38;5;33m",
    "CYAN": "\033[38;5;37m",
    "GREEN": "\033[38;5;100m",
    "SOLARIZED_BASE03": "\033[38;5;234m",
    "SOLARIZED_BASE02": "\033[38;5;235m",
    "SOLARIZED_BASE01": "\033[38;5;240m",
    "SOLARIZED_BASE00": "\033[38;5;241m",
    "SOLARIZED_BASE0": "\033[38;5;246m",
    "SOLARIZED_BASE1": "\033[38;5;247m",
    "SOLARIZED_BASE2": "\033[38;5;254m",
    "SOLARIZED_BASE3": "\033[38;5;230m",
    "SOLARIZED_YELLOW": "\033[38;5;136m",
    "SOLARIZED_ORANGE": "\033[38;5;166m",
    "SOLARIZED_RED": "\033[38;5;160m",
    "SOLARIZED_MAGENTA": "\033[38;5;168m",
    "SOLARIZED_VIOLET": "\033[38;5;61m",
    "SOLARIZED_BLUE": "\033[38;5;33m",
    "SOLARIZED_CYAN": "\033[38;5;37m",
    "SOLARIZED_GREEN": "\033[38;5;100m",
}

for _name, _value in SOLARIZED.items():
    if not hasattr(Fore, _name):
        setattr(Fore, _name, _value)

if not hasattr(Fore, "RESET"):
    Fore.RESET = "\033[0m"
if not hasattr(Style, "RESET_ALL"):
    Style.RESET_ALL = "\033[0m"

ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def safe_getlogin():
    try:
        return os.getlogin()
    except Exception:
        return os.environ.get("USER") or os.environ.get("USERNAME") or "Unknown"


def visible_len(text):
    return len(ANSI_RE.sub("", str(text)))


def clamp_text(text, max_width):
    text = str(text)
    if visible_len(text) <= max_width:
        return text
    plain = ANSI_RE.sub("", text)
    if max_width <= 1:
        return plain[:max_width]
    return plain[: max_width - 1] + "…"


def pad_visible(text, width):
    text = str(text)
    plain = ANSI_RE.sub("", text)
    if len(plain) >= width:
        trimmed = clamp_text(text, width)
        return trimmed + (" " * max(0, width - visible_len(trimmed)))
    return text + (" " * max(0, width - len(plain)))


def get_user_full_name():
    username = os.environ.get("USERNAME") or os.environ.get("USER")
    if os.name == "nt" and username:
        try:
            out = subprocess.check_output(
                ["wmic", "useraccount", "where", f"name='{username}'", "get", "FullName"],
                stderr=subprocess.DEVNULL,
                universal_newlines=True,
            )
            lines = [line.strip() for line in out.splitlines() if line.strip() and "FullName" not in line]
            if lines:
                full = lines[0]
                if full and full != username:
                    return f"{full} ({username})"
                if full:
                    return full
        except Exception:
            pass

        try:
            out = subprocess.check_output(
                ["net", "user", username],
                stderr=subprocess.DEVNULL,
                universal_newlines=True,
            )
            for line in out.splitlines():
                if "Full Name" in line:
                    full = line.split("Full Name", 1)[1].strip()
                    if full and full != username:
                        return f"{full} ({username})"
                    if full:
                        return full
        except Exception:
            pass

        try:
            out = subprocess.check_output(
                ["powershell", "-NoProfile", "-Command", f"(Get-LocalUser -Name '{username}').FullName"],
                stderr=subprocess.DEVNULL,
                universal_newlines=True,
            )
            out = out.strip()
            if out:
                if out != username:
                    return f"{out} ({username})"
                return out
        except Exception:
            pass

    try:
        import pwd
        pw = pwd.getpwuid(os.getuid())
        gecos = (pw.pw_gecos or "").split(",")[0].strip()
        if gecos:
            if username and gecos != username:
                return f"{gecos} ({username})"
            return gecos
    except Exception:
        pass

    return safe_getlogin()


def format_bytes(value):
    if value is None:
        return "Unknown"
    value = float(value)
    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:0.1f} {unit}"
        value /= 1024
    return f"{value:.1f} PB"


def format_timedelta(seconds):
    if seconds is None:
        return "Unknown"
    seconds = int(seconds)
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, secs = divmod(rem, 60)
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    parts.append(f"{secs}s")
    return " ".join(parts)


def get_ip_addresses():
    ips = set()
    try:
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None):
            addr = info[4][0]
            if addr.startswith("127.") or addr == "::1":
                continue
            ips.add(addr)
    except Exception:
        pass

    if not ips:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(0.5)
            sock.connect(("8.8.8.8", 80))
            ips.add(sock.getsockname()[0])
            sock.close()
        except Exception:
            pass
    return sorted(ips) if ips else ["Unknown"]


def get_uptime():
    if psutil:
        try:
            return time.time() - psutil.boot_time()
        except Exception:
            pass

    if os.path.exists("/proc/uptime"):
        try:
            with open("/proc/uptime", "r", encoding="utf-8", errors="ignore") as f:
                return float(f.readline().split()[0])
        except Exception:
            pass

    if os.name == "nt":
        try:
            out = subprocess.check_output(
                ["wmic", "os", "get", "LastBootUpTime"],
                stderr=subprocess.DEVNULL,
                universal_newlines=True,
            )
            lines = [line.strip() for line in out.splitlines() if line.strip() and "LastBootUpTime" not in line]
            if lines:
                ts = lines[0]
                dt = datetime.datetime.strptime(ts[:14], "%Y%m%d%H%M%S")
                return (datetime.datetime.now() - dt).total_seconds()
        except Exception:
            pass

    return None


def get_disk_info():
    root = "/" if os.name != "nt" else os.environ.get("SystemDrive", "C:") + "\\"
    try:
        usage = shutil.disk_usage(root)
        return {
            "total": usage.total,
            "used": usage.used,
            "free": usage.free,
            "mount": root,
        }
    except Exception:
        return {"total": None, "used": None, "free": None, "mount": root}


def get_memory_info():
    if psutil:
        try:
            vm = psutil.virtual_memory()
            return {
                "total": vm.total,
                "available": vm.available,
                "used": vm.used,
                "percent": vm.percent,
            }
        except Exception:
            pass
    return {"total": None, "available": None, "used": None, "percent": None}


def get_cpu_info():
    physical = None
    logical = os.cpu_count()
    if psutil:
        try:
            physical = psutil.cpu_count(logical=False)
        except Exception:
            physical = None
        try:
            logical = psutil.cpu_count(logical=True) or logical
        except Exception:
            pass

    freq = None
    if psutil:
        try:
            f = psutil.cpu_freq()
            freq = f.current if f else None
        except Exception:
            freq = None

    load = None
    if hasattr(os, "getloadavg"):
        try:
            load = os.getloadavg()
        except Exception:
            load = None

    return {"physical": physical, "logical": logical, "freq_mhz": freq, "load_avg": load}


def get_processor_model():
    try:
        import cpuinfo
        info = cpuinfo.get_cpu_info()
        brand = info.get("brand_raw") or info.get("brand")
        if brand:
            return brand.strip()
    except Exception:
        pass

    try:
        if os.name != "nt" and os.path.exists("/proc/cpuinfo"):
            with open("/proc/cpuinfo", "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    lower = line.lower()
                    if lower.startswith("model name") or lower.startswith("processor"):
                        parts = line.split(":", 1)
                        if len(parts) == 2:
                            val = parts[1].strip()
                            if val:
                                return val
    except Exception:
        pass

    try:
        if sys.platform == "darwin":
            out = subprocess.check_output(
                ["sysctl", "-n", "machdep.cpu.brand_string"],
                stderr=subprocess.DEVNULL,
                universal_newlines=True,
            )
            out = out.strip()
            if out:
                return out
    except Exception:
        pass

    try:
        if os.name == "nt":
            out = subprocess.check_output(
                ["wmic", "cpu", "get", "Name"],
                stderr=subprocess.DEVNULL,
                universal_newlines=True,
            )
            lines = [line.strip() for line in out.splitlines() if line.strip()]
            if len(lines) >= 2:
                return lines[1]
    except Exception:
        pass

    try:
        p = platform.processor()
        if p:
            return p
    except Exception:
        pass

    try:
        p2 = platform.uname().processor
        if p2:
            return p2
    except Exception:
        pass

    return "Unknown"


def get_disk_partitions():
    mounts = []
    try:
        if psutil:
            for part in psutil.disk_partitions(all=False):
                try:
                    usage = psutil.disk_usage(part.mountpoint)
                    mounts.append(
                        {"device": part.device, "mount": part.mountpoint, "fstype": part.fstype,
                         "total": usage.total, "used": usage.used, "free": usage.free,
                         "percent": (usage.used / usage.total * 100.0) if usage.total else 0}
                    )
                except Exception:
                    mounts.append(
                        {"device": part.device, "mount": part.mountpoint, "fstype": part.fstype,
                         "total": None, "used": None, "free": None, "percent": None}
                    )
            return mounts
    except Exception:
        pass

    root_usage = get_disk_info()
    mounts.append(
        {"device": "root", "mount": root_usage.get("mount", "/"), "fstype": "unknown",
         "total": root_usage.get("total"), "used": root_usage.get("used"), "free": root_usage.get("free"), "percent": None}
    )
    return mounts


def get_network_interfaces():
    if not psutil:
        return []
    try:
        data = []
        for name, addrs in psutil.net_if_addrs().items():
            ips = [addr.address for addr in addrs if getattr(addr, "family", None) in (socket.AF_INET, socket.AF_INET6)]
            data.append({"name": name, "ips": ips})
        return data
    except Exception:
        return []


def get_top_processes(limit=5):
    if not psutil:
        return []
    try:
        proc_list = []
        for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent", "username", "cmdline"]):
            try:
                info = proc.info
                proc_list.append(
                    {"pid": info.get("pid"), "name": info.get("name") or "unknown",
                     "cpu": info.get("cpu_percent") or 0.0, "memory": info.get("memory_percent") or 0.0,
                     "user": info.get("username") or "unknown",
                     "cmdline": " ".join(info.get("cmdline") or [])[:80]}
                )
            except Exception:
                continue

        proc_list.sort(key=lambda p: (p["memory"], p["cpu"]), reverse=True)
        return proc_list[:limit]
    except Exception:
        return []


def get_system_health(mem=None, disk=None, cpu=None):
    mem = mem or get_memory_info()
    disk = disk or get_disk_info()
    cpu = cpu or get_cpu_info()

    warnings = []
    critical = []

    if mem.get("percent") is not None:
        if mem["percent"] >= 90:
            critical.append("memory usage")
        elif mem["percent"] >= 75:
            warnings.append("memory usage")

    if disk.get("used") is not None and disk.get("total"):
        used_pct = (disk["used"] / disk["total"]) * 100.0
        if used_pct >= 95:
            critical.append("disk usage")
        elif used_pct >= 80:
            warnings.append("disk usage")

    if isinstance(cpu.get("load_avg"), tuple) and cpu["load_avg"]:
        if cpu["load_avg"][0] > 2:
            warnings.append("CPU load")

    if critical:
        return "Critical"
    if warnings:
        return "Warning"
    return "Healthy"


def get_os_label():
    system = platform.system() or "Unknown"
    release = platform.release() or "Unknown"
    if system == "Windows":
        return f"{system} {release}"
    if system == "Linux":
        return f"{system} {release}"
    if system == "Darwin":
        return f"macOS {release}"
    return f"{system} {release}"


def get_sys_info():
    uname = platform.uname()
    memory = get_memory_info()
    disk = get_disk_info()
    cpu = get_cpu_info()
    uptime = get_uptime()
    tzname = datetime.datetime.now().astimezone().tzname() or "Unknown"
    locale = os.environ.get("LANG") or os.environ.get("LC_ALL") or os.environ.get("LC_CTYPE") or "Unknown"
    shell = os.environ.get("SHELL") or os.environ.get("COMSPEC") or "Unknown"

    info = {
        "Operating system": get_os_label(),
        "Platform": platform.platform(),
        "Kernel version": uname.release or "Unknown",
        "Architecture": uname.machine or "Unknown",
        "Processor type": get_processor_model() or "Unknown",
        "Python version": platform.python_version(),
        "Python executable": sys.executable or "Unknown",
        "User": get_user_full_name(),
        "Hostname": socket.gethostname(),
        "IP addresses": ", ".join(get_ip_addresses()),
        "Uptime": format_timedelta(uptime),
        "Boot time": (
            (datetime.datetime.now() - datetime.timedelta(seconds=int(uptime))).isoformat(sep=" ", timespec="seconds")
            if uptime is not None
            else "Unknown"
        ),
        "Timezone": tzname,
        "Locale": locale,
        "Shell": shell,
        "CPU (physical/logical)": f"{cpu.get('physical') or '?'} / {cpu.get('logical') or '?'}",
        "CPU frequency (MHz)": f"{cpu['freq_mhz']:.1f}" if cpu.get("freq_mhz") else "Unknown",
        "Load average (1m,5m,15m)": (
            ", ".join(f"{x:.2f}" for x in cpu["load_avg"]) if cpu.get("load_avg") else "Unknown"
        ),
        "Memory (total/available/used)": (
            f"{format_bytes(memory.get('total'))} / {format_bytes(memory.get('available'))} / {format_bytes(memory.get('used'))}"
            if memory.get("total") is not None
            else "Unknown"
        ),
        "Memory percent": f"{memory.get('percent')}%" if memory.get("percent") is not None else "Unknown",
        "Disk": (
            f"{format_bytes(disk.get('total'))} total, {format_bytes(disk.get('free'))} free ({disk.get('mount')})"
            if disk.get("total") is not None
            else "Unknown"
        ),
        "Disk percent": (
            f"{((disk['used'] / disk['total']) * 100.0):.1f}%"
            if disk.get("used") is not None and disk.get("total")
            else "Unknown"
        ),
        "System status": get_system_health(memory, disk, cpu),
    }
    return info


def colorize(text, color):
    if not COLOR_AVAILABLE:
        return text
    return f"{color}{text}{Fore.RESET}"


def color_metric(value, warn=75, critical=90, use_color=True):
    if not use_color or not COLOR_AVAILABLE or value is None:
        return str(value)
    try:
        pct = float(value)
    except (TypeError, ValueError):
        return str(value)

    if pct >= critical:
        return f"{Fore.RED}{value}{Fore.RESET}"
    if pct >= warn:
        return f"{Fore.YELLOW}{value}{Fore.RESET}"
    return f"{Fore.GREEN}{value}{Fore.RESET}"


def render_compact(info, use_color=True):
    status = get_system_health()
    color = Fore.GREEN if status == "Healthy" else Fore.YELLOW if status == "Warning" else Fore.RED
    title = "SysVer 2.0"
    if use_color and COLOR_AVAILABLE:
        title = colorize(title, Fore.CYAN)
        status = colorize(status, color)

    lines = [
        f"{title} - {status}",
        f"{info.get('Operating system', 'Unknown')} | {info.get('User', 'Unknown')}@{info.get('Hostname', 'Unknown')}",
        f"CPU: {info.get('CPU (physical/logical)', 'Unknown')} | Mem: {info.get('Memory (total/available/used)', 'Unknown')}",
        f"Disk: {info.get('Disk', 'Unknown')} | Uptime: {info.get('Uptime', 'Unknown')}",
    ]
    return "\n".join(lines)


def render_dashboard(info, use_color=True, top_processes=None, partitions=None, interfaces=None):
    health = get_system_health(get_memory_info(), get_disk_info(), get_cpu_info())
    mem = get_memory_info()
    disk = get_disk_info()
    cpu = get_cpu_info()
    health_label = health
    health_color = Fore.GREEN if health == "Healthy" else Fore.YELLOW if health == "Warning" else Fore.RED

    left = [
        ("OS", info.get("Operating system", "Unknown")),
        ("Kernel", info.get("Kernel version", "Unknown")),
        ("Arch", info.get("Architecture", "Unknown")),
        ("Processor", info.get("Processor type", "Unknown")),
        ("Python", info.get("Python version", "Unknown")),
        ("User", info.get("User", "Unknown")),
    ]

    right = [
        ("Hostname", info.get("Hostname", "Unknown")),
        ("IP", info.get("IP addresses", "Unknown")),
        ("Uptime", info.get("Uptime", "Unknown")),
        ("Boot", info.get("Boot time", "Unknown")),
        ("CPU", info.get("CPU (physical/logical)", "Unknown")),
        ("CPU Freq", info.get("CPU frequency (MHz)", "Unknown")),
    ]

    width = 96
    lines = []
    header = "SysVer 2.0"
    if use_color and COLOR_AVAILABLE:
        header = colorize(header, Fore.CYAN)
    lines.append(f"+{'-' * (width + 2)}+")
    lines.append(f"| {header:<{width}} |")
    status_line = f"Status: {health_label}"
    if use_color and COLOR_AVAILABLE:
        status_line = colorize(status_line, health_color)
    lines.append(f"| {status_line:<{width}} |")
    lines.append(f"+{'-' * (width + 2)}+")

    max_rows = max(len(left), len(right))
    left_col = width // 2 - 1
    right_col = width // 2 - 1
    for i in range(max_rows):
        l = left[i] if i < len(left) else ("", "")
        r = right[i] if i < len(right) else ("", "")
        l_key, l_val = l
        r_key, r_val = r

        l_text = f"{l_key}: {l_val}" if l_key else ""
        r_text = f"{r_key}: {r_val}" if r_key else ""

        if use_color and COLOR_AVAILABLE:
            l_text = colorize(l_text, Fore.CYAN if i % 2 == 0 else Fore.YELLOW)
            r_text = colorize(r_text, Fore.CYAN if i % 2 == 0 else Fore.YELLOW)

        l_text = pad_visible(l_text, left_col)
        r_text = pad_visible(r_text, right_col)
        lines.append(f"| {l_text} | {r_text} |")

    lines.append(f"+{'-' * (width + 2)}+")

    load_avg = cpu.get("load_avg")
    load_first = load_avg[0] if isinstance(load_avg, (tuple, list)) and load_avg else None
    mem_pct = mem.get("percent")
    disk_pct = None
    if disk.get("used") is not None and disk.get("total"):
        disk_pct = (disk["used"] / disk["total"]) * 100.0

    system_rows = [
        ("Load Avg", info.get("Load average (1m,5m,15m)", "Unknown"), load_first, 2.0, 4.0),
        ("Memory", info.get("Memory (total/available/used)", "Unknown"), mem_pct, 75.0, 90.0),
        ("Disk", info.get("Disk", "Unknown"), disk_pct, 80.0, 95.0),
    ]
    for key, value, metric_value, warn, critical in system_rows:
        if use_color and COLOR_AVAILABLE and metric_value is not None:
            value_color = Fore.GREEN if metric_value < warn else Fore.YELLOW if metric_value < critical else Fore.RED
            value_text = colorize(value, value_color)
        else:
            value_text = value

        if use_color and COLOR_AVAILABLE:
            key_text = colorize(key, Fore.CYAN)
            lines.append(f"| {pad_visible(key_text, 20)} {pad_visible(value_text, width - 22)} |")
        else:
            lines.append(f"| {key:<20} {value:<{width - 22}} |")

    lines.append(f"+{'-' * (width + 2)}+")

    if top_processes:
        lines.append("| Top Processes |")
        for proc in top_processes:
            label = f"{proc['name']} ({proc['pid']})"
            metric = f"CPU {proc['cpu']:.1f}%  RAM {proc['memory']:.1f}%"
            if use_color and COLOR_AVAILABLE:
                label = colorize(label, Fore.GREEN)
                metric = (
                    f"CPU {color_metric(proc['cpu'], 50, 80, use_color=True)}%  "
                    f"RAM {color_metric(proc['memory'], 50, 80, use_color=True)}%"
                )
            lines.append(f"| {pad_visible(label, 30)} {pad_visible(metric, width - 32)} |")
        lines.append(f"+{'-' * (width + 2)}+")

    if partitions:
        lines.append("| Filesystems |")
        for part in partitions[:3]:
            mount = part.get("mount", "/")
            total = format_bytes(part.get("total")) if part.get("total") is not None else "Unknown"
            used = format_bytes(part.get("used")) if part.get("used") is not None else "Unknown"
            pct = part.get("percent")
            pct_text = f"{pct:.1f}%" if pct is not None else "Unknown"
            if use_color and COLOR_AVAILABLE and pct is not None:
                pct_text = color_metric(pct, 80, 95, use_color=True) + "%"
            lines.append(f"| {mount:<20} {total:<12} used {used:<12} [{pct_text}] |")
        lines.append(f"+{'-' * (width + 2)}+")

    if interfaces:
        lines.append("| Interfaces |")
        for iface in interfaces[:4]:
            ips = ", ".join(iface.get("ips", [])[:2])
            if not ips:
                ips = "No IP"
            lines.append(f"| {iface.get('name', 'unknown'):<12} {ips:<{width - 14}} |")
        lines.append(f"+{'-' * (width + 2)}+")

    return "\n".join(lines)


def render_box(info, use_color=True):
    items = list(info.items())
    width = 132
    label_width = 30
    border = "+" + "-" * (width - 2) + "+"
    lines = [border]

    title = "SysVer 2.0"
    if use_color and COLOR_AVAILABLE:
        title = colorize(title, Fore.CYAN)
    lines.append(f"| {title:<{width - 4}} |")
    lines.append(border)

    for key, value in items:
        label = f"{key}:"
        value_text = str(value)

        if visible_len(label) > label_width:
            label = clamp_text(label, label_width)
        if visible_len(value_text) > (width - label_width - 9):
            value_text = clamp_text(value_text, width - label_width - 9)

        if use_color and COLOR_AVAILABLE:
            label_display = colorize(label, Fore.CYAN)
            padded = max(0, width - 4 - visible_len(f"{label_display}: {value_text}"))
            lines.append(f"| {label_display}: {value_text}{' ' * padded} |")
        else:
            padded = max(0, width - 4 - visible_len(f"{label} {value_text}"))
            lines.append(f"| {label:<{label_width}} {value_text}{' ' * padded} |")

    lines.append(border)
    return "\n".join(lines)


def render_table(info, use_color=True):
    items = list(info.items())
    key_w = max(len(k) for k, _ in items)
    val_w = max(len(str(v)) for _, v in items)
    sep = f"+-{'-'*key_w}-+-{'-'*val_w}-+"
    lines = [sep]
    for k, v in items:
        if use_color and COLOR_AVAILABLE:
            k_display = Fore.CYAN + k.ljust(key_w) + Fore.RESET
        else:
            k_display = k.ljust(key_w)
        lines.append(f"| {k_display} | {str(v).ljust(val_w)} |")
    lines.append(sep)
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description="SysVer 2.0 - advanced system information utility")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    parser.add_argument("--format", choices=["box", "table", "dashboard", "compact"], default="dashboard", help="Output format")
    parser.add_argument("--no-color", action="store_true", help="Disable ANSI colors")
    parser.add_argument("--verbose", action="store_true", help="Show additional debug information")
    parser.add_argument("--top-processes", type=int, default=5, help="Include N top processes")
    parser.add_argument("--export", metavar="PATH", help="Write JSON snapshot to file")
    parser.add_argument("--theme", choices=["auto", "dark", "light"], default="auto", help="Color theme preference")
    args = parser.parse_args(argv)

    info = get_sys_info()
    use_color = not args.no_color and sys.stdout.isatty()

    if args.export:
        try:
            with open(args.export, "w", encoding="utf-8") as f:
                json.dump(info, f, indent=2)
        except Exception as exc:
            print(f"Failed to export JSON: {exc}", file=sys.stderr)
            return 1

    if args.json:
        print(json.dumps(info, indent=2))
        return 0

    top_processes = get_top_processes(args.top_processes) if args.top_processes > 0 else []
    partitions = get_disk_partitions()
    interfaces = get_network_interfaces()

    if args.format == "box":
        out = render_box(info, use_color=use_color)
    elif args.format == "table":
        out = render_table(info, use_color=use_color)
    elif args.format == "compact":
        out = render_compact(info, use_color=use_color)
    else:
        out = render_dashboard(info, use_color=use_color, top_processes=top_processes, partitions=partitions, interfaces=interfaces)

    if not args.verbose:
        try:
            os.system("cls" if os.name == "nt" else "clear")
        except Exception:
            pass

    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
