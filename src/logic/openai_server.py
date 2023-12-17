import json
import logging
import os
from openai import OpenAI
from time import sleep, time

from logic.docker_server import DockerServer
from model.openai_tool import OpenAIFunction, OpenAIFunctionParameter, OpenAIFunctionParameterProperty, OpenAITool
from model.run_result import RunResult

class OpenAIServer:
    def __init__(self, token: str, model="gpt-4-1106-preview"):
        self.model = model
        self.reports = []
        self.jobs = {}
        self.runningLock = False
        self.server = DockerServer("ubuntu", "openai", 1.0, "512mb", "512mb")
        self.logger = logging.getLogger(self.__class__.__name__)
        self.client = OpenAI(api_key=token)

    def exec_command(self, cmd) -> dict[str, any]:
        proc = self.server.runCommand(cmd=cmd)
        output: str = proc.stdout.decode()
        if len(output) > 500:
            output = output[-500:]
        outputList = output.split("\n")
        if len(outputList) > 5:
            outputList = outputList[-5:]
        output = "\n".join(outputList)
        if proc.returncode == 124:
            return RunResult(returncode=124, output="Sorry, timeout").dict()
        return RunResult(returncode=proc.returncode, output=output).dict()
    
    def change_directory(self, path):
        res = self.server.changeWorkDir(path)
        return {"result": "ok" if res else "failed"}
    
    def call_myself(self, unixtime: int, message=""):
        if unixtime < int(time()):
            return {"result": "failed", "message": "Past time specified"}
        self.jobs[unixtime] = message
        return {"result": "ok"}
    
    def write_report(self, description: str):
        self.reports.append(description=description)
        return {"result": "ok"}
    
    def write_file(self, path: str, value: str, mode: str):
        return {"result": "ok" if self.server.writeTextFile(path, value, mode) else "failed"}
    
    def open_port(self, port: int):
        message = ""
        if port in self.server.ports:
            message = "already opened"
        if port // 10000 == 3:
            message = "reserved port"
        if message == "":
            self.server.ports.append(port)
        return {"result": "ok" if message == "" else "failed", "message": message}
    
    def close_port(self, port: int):
        message = ""
        if not port in self.server.ports:
            message = "the port is not opened"
        if message == "":
            self.server.ports.remove(port)
        return {"result": "ok" if message == "" else "failed", "message": message}
    
    @staticmethod
    def generateTools() -> list[dict]:
        tools = [
            OpenAITool(
                function=OpenAIFunction(
                    name="exec_command",
                    description="Executes the given command. Can check output of up to 500 characters or 5 lines. Keyboard input is not available. Recommended to use `echo` command. Timeout is 1h. Work folder can be changed with `change_directory` Function.",
                    parameters=OpenAIFunctionParameter(
                        properties={
                            "cmd": OpenAIFunctionParameterProperty(
                                type="string"
                            )
                        },
                        required=["cmd"]
                    ),
                )
            ),
            OpenAITool(
                function=OpenAIFunction(
                    name="change_directory",
                    description="Change the working directory to the given folder path.",
                    parameters=OpenAIFunctionParameter(
                        properties={
                            "path": OpenAIFunctionParameterProperty(
                                type="string"
                            )
                        },
                        required=["path"]
                    ),
                )
            ),
            OpenAITool(
                function=OpenAIFunction(
                    name="call_myself",
                    description="This function will call you again at the given time.",
                    parameters=OpenAIFunctionParameter(
                        properties={
                            "unixtime": OpenAIFunctionParameterProperty(
                                type="int",
                                description="I recommend calculating it first using the command."
                            ),
                            "message": OpenAIFunctionParameterProperty(
                                type="string",
                                description="Message for next execution. What you want the next you to do."
                            )
                        },
                        required=["unixtime"]
                    ),
                )
            ),
            OpenAITool(
                function=OpenAIFunction(
                    name="write_report",
                    description="Once you have completed the instructions, be sure to do it at the end.",
                    parameters=OpenAIFunctionParameter(
                        properties={
                            "description": OpenAIFunctionParameterProperty(
                                type="string",
                                description="A short one-sentence explanation of what you did."
                            )
                        },
                        required=["description"]
                    ),
                )
            ),
            OpenAITool(
                function=OpenAIFunction(
                    name="write_file",
                    description="Creating or appending a text file",
                    parameters=OpenAIFunctionParameter(
                        properties={
                            "path": OpenAIFunctionParameterProperty(
                                type="string"
                            ),
                            "value": OpenAIFunctionParameterProperty(
                                type="string",
                                description="Only text available"
                            ),
                            "mode": OpenAIFunctionParameterProperty(
                                type="string",
                                enum=["create", "append"]
                            )
                        },
                        required=["path", "value", "mode"]
                    )
                )
            ),
            OpenAITool(
                function=OpenAIFunction(
                    name="open_port",
                    description="Open a port for the user.",
                    parameters=OpenAIFunctionParameter(
                        properties={
                            "port": OpenAIFunctionParameterProperty(
                                type="int",
                            )
                        },
                        required=["port"]
                    ),
                )
            ),
            OpenAITool(
                function=OpenAIFunction(
                    name="close_port",
                    description="Close the ports you opened for the user",
                    parameters=OpenAIFunctionParameter(
                        properties={
                            "port": OpenAIFunctionParameterProperty(
                                type="int",
                            )
                        },
                        required=["port"]
                    ),
                )
            )
        ]
        return [tool.dict() for tool in tools]
    
    async def run(self, prompt: str):
        while self.runningLock:
            sleep(1)
        try:
            self.runningLock = True
            pastActionsPrompt = "" if len(self.reports) > 0 else "N/A"
            if len(self.reports) > 0:
                for report in self.reports:
                    pastActionsPrompt += f"- {report}\n"
            portsPrompt = "" if len(self.server.ports) > 0 else "N/A"
            if len(self.server.ports) > 0:
                for port in self.server.ports:
                    portsPrompt += f"{port},"
            systemPrompt = f"You are the administrator of a Linux server.\n\nServer specs:\nCPU: {self.server.cpu}\nRAM: {self.server.ram.upper()}\nSwap: {self.server.swap.upper()}\nUser: root\n\nUse functions to respond to requests from users.\nBelow is a summary of the actions you have taken in the past.\n{pastActionsPrompt}\n\nPorts open to the user: {portsPrompt}"
            messages = [{"role": "system", "content": systemPrompt}, {"role": "user", "content": f"Here's a request from a user: {prompt}"}]
            while True:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=self.generateTools(),
                    tool_choice="auto"
                )
                response_message = response.choices[0].message
                tool_calls = response_message.tool_calls
                shouldExit = False
                if tool_calls:
                    for tool_call in tool_calls:
                        func = getattr(self, tool_call.function.name)
                        shouldExit = tool_call.function.name == "write_report"
                        if callable(func):
                            functionResponse: dict = func(**json.loads(tool_call.function.arguments))
                            messages.append({
                                "tool_call_id": tool_call.id,
                                "role": "tool",
                                "name": tool_call.function.name,
                                "content": functionResponse
                            })
                if shouldExit: break
        finally:
            self.runningLock = False