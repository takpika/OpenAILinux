import logging
import subprocess
import base64

class DockerServer:
    def __init__(
            self,
            containerName: str = "ubuntu-systemd",
            id: str = "openai",
            cpu: float = 2.0,
            ram: str = "2gb",
            swap: str = "2gb"
        ):
        self.containerName = containerName
        self.id = id
        self.cpu = cpu
        self.ram = ram
        self.swap = swap
        self._running = False
        self.workDir = "/root"
        self.homeDir = "/root"
        self.ports = []
        self.logger = logging.getLogger(self.__name__ + "-" + self.containerName)
        if not self.checkDockerInstalled():
            self.logger.error("Docker is not installed")
            exit(1)

    def start(self):
        if not self.isRunning():
            logging.info(f"Starting Container")
            subprocess.run(["docker", "run", "--name", f"{self.containerName}.{self.id}", "-d", "--rm", "--privileged", "-v", "/sys/fs/cgroup:/sys/fs/croup:ro", f"--memory={self.ram}", f"--memory-swap={self.swap}", f"--cpus={self.cpu}", self.containerName])
            for port in self.ports:
                self.openPort(port)
        self._running = True
    
    def stop(self):
        if self.isRunning():
            logging.info(f"Stopping Container")
            subprocess.run(["docker", "stop", f"{self.containerName}.{self.id}"])
        for port in self.ports:
            self.closePort(port)
        self._running = False

    def checkDockerInstalled(self) -> bool:
        proc = subprocess.run(["docker", "--version"], capture_output=True, text=True)
        return proc.returncode == 0

    def isRunning(self) -> bool:
        proc = subprocess.run(["docker", "ps", "-a", "--filter", "name=" + f"{self.containerName}.{self.id}", "--format", "{{.Names}}"], capture_output=True, text=True)
        return len(proc.stdout) > 0
    
    def runCommand(self, cmd: str) -> subprocess.CompletedProcess[str]:
        proc = subprocess.run(["docker", "exec", "-w", self.workDir, f"{self.containerName}.{self.id}", "timeout", str(600), "bash", "-c", "cmd"], capture_output=True, text=True)
        return proc
    
    def checkFolder(self, path: str) -> bool:
        proc = self.runCommand(f"test -d {path}")
        return proc.returncode == 0
    
    def checkFile(self, path: str) -> bool:
        proc = self.runCommand(f"test -f {path}")
        return proc.returncode == 0

    def appendPath(self, path: str) -> str | None:
        givenWorkDirList = path.split("/")
        if len(givenWorkDirList) < 1:
            return None
        if not path[0] == "/" and givenWorkDirList[0] == ".":
            givenWorkDirList[0] = self.workDir
        if givenWorkDirList[0] == "~":
            givenWorkDirList[0] = self.homeDir
        newPath = ""
        for i in range(len(givenWorkDirList)):
            if len(givenWorkDirList) < 1:
                continue
            if i > 0 and givenWorkDirList[i] == "~":
                return None
            if givenWorkDirList[i] == ".":
                pass
            elif givenWorkDirList[i] == "..":
                newPathList = newPath.split("/")
                newPath = "/".join(newPathList[:-1])
                if len(newPath) == 0:
                    newPath = "/"
                if newPath[0] != "/":
                    newPath = "/" + newPath
            else:
                newPath += ("/" if not (len(newPath) == 0 or newPath == "/" or i == 0) else "") + givenWorkDirList[i]
            if newPath[-1] == "/" and not newPath == "/":
                newPath = newPath[:-1]
        return newPath
    
    def changeWorkDir(self, path: str) -> bool:
        newPath = self.appendPath(path)
        if not self.checkFolder(newPath):
            return False
        self.workDir = newPath
        return True
    
    def writeTextFile(self, path: str, value: str, mode: str) -> bool:
        fullPath = self.appendPath(path)
        b64 = base64.b64encode(value.encode()).decode()
        p = ">" if mode == "create" else ">>"
        return self.runCommand(f"echo {b64} | base64 -d {p} {fullPath}").returncode == 0
    
    def writeRawFile(self, path: str, value: bytes) -> bool:
        fullPath = self.appendPath(path)
        b64 = base64.b64encode(value).decode()
        return self.runCommand(f"echo {b64} | base64 -d > {fullPath}").returncode == 0
    
    def checkIPAddress(self) -> str | None:
        proc = self.runCommand("ip addr show eth0 | grep -oP '(?<=inet\s)\d+(\.\d+){3}'")
        if proc.returncode != 0:
            return None
        return proc.stdout.strip()
    
    def openPort(self, port: int) -> bool:
        if port in self.ports:
            return False
        mappedPort = port % 10000 + 30000
        subprocess.run(["iptables", "-t", "nat", "-A", "DOCKER", "!", "-i", "docker0", "-p", "tcp", "-m", "tcp", "--dport", str(mappedPort), "-j", "DNAT", "--to-destination", f"{self.checkIPAddress()}:{port}"])
        subprocess.run(["iptables", "-t", "nat", "-A", "POSTROUTING", "-p", "tcp", "-m", "tcp", "--dport", str(port), "-j", "MASQUERADE"])
        self.ports.append(port)
        return True
    
    def closePort(self, port: int) -> bool:
        if not port in self.ports:
            return False
        mappedPort = port % 10000 + 30000
        subprocess.run(["iptables", "-t", "nat", "-D", "DOCKER", "!", "-i", "docker0", "-p", "tcp", "-m", "tcp", "--dport", str(mappedPort), "-j", "DNAT", "--to-destination", f"{self.checkIPAddress()}:{port}"])
        subprocess.run(["iptables", "-t", "nat", "-D", "POSTROUTING", "-p", "tcp", "-m", "tcp", "--dport", str(port), "-j", "MASQUERADE"])
        self.ports.remove(port)
        return True