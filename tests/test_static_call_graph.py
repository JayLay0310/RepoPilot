import tempfile
import unittest
from pathlib import Path

from backend.tools.static_call_graph import build_static_call_graph, trace_static_call_chain


class StaticCallGraphTests(unittest.TestCase):
    def test_python_import_call_resolution(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "app.py").write_text(
                "from service import handle\n\n"
                "def route():\n"
                "    return handle()\n",
                encoding="utf-8",
            )
            (repo / "service.py").write_text(
                "def handle():\n"
                "    return 'ok'\n",
                encoding="utf-8",
            )

            graph = build_static_call_graph(str(repo), force_rebuild=True)
            self.assertIn(
                {"from": "app.route", "to": "service.handle", "line": 4, "call": "handle", "resolver": "python-ast"},
                graph["edges"],
            )
            cached = build_static_call_graph(str(repo))
            self.assertEqual(cached["stats"]["cache"], "hit")

    def test_incremental_cache_reuses_unchanged_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "a.py").write_text("def a():\n    return b()\n", encoding="utf-8")
            (repo / "b.py").write_text("def b():\n    return 'b'\n", encoding="utf-8")

            build_static_call_graph(str(repo), force_rebuild=True)
            (repo / "a.py").write_text("def a():\n    return b()\n\ndef c():\n    return a()\n", encoding="utf-8")
            graph = build_static_call_graph(str(repo))

            self.assertEqual(graph["stats"]["parsed_files"], 1)
            self.assertEqual(graph["stats"]["reused_files"], 1)

    def test_fastapi_entrypoint_resolution(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "api.py").write_text(
                "from fastapi import APIRouter\n\n"
                "router = APIRouter()\n\n"
                "@router.post('/tasks')\n"
                "def create_task():\n"
                "    return run_workflow()\n\n"
                "def run_workflow():\n"
                "    return 'ok'\n",
                encoding="utf-8",
            )

            graph = build_static_call_graph(str(repo), force_rebuild=True)
            self.assertEqual(graph["stats"]["fastapi_entrypoints"], 1)
            self.assertEqual(graph["fastapi"]["entrypoints"][0]["method"], "POST")
            self.assertEqual(graph["fastapi"]["entrypoints"][0]["path"], "/tasks")

            chain = trace_static_call_chain(str(repo), "run_workflow")
            self.assertEqual(chain["entrypoints"][0]["handler"], "api.create_task")

    def test_spring_controller_service_resolution(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            package_dir = repo / "src" / "main" / "java" / "com" / "example"
            package_dir.mkdir(parents=True)
            (package_dir / "UserController.java").write_text(
                """
package com.example;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/users")
public class UserController {
    @Autowired
    private UserService userService;

    @GetMapping("/{id}")
    public String getUser() {
        return userService.findUser();
    }
}
""",
                encoding="utf-8",
            )
            (package_dir / "UserService.java").write_text(
                """
package com.example;

import org.springframework.stereotype.Service;

@Service
public class UserService {
    public String findUser() {
        return "ok";
    }
}
""",
                encoding="utf-8",
            )

            graph = build_static_call_graph(str(repo), force_rebuild=True)
            self.assertEqual(graph["stats"]["spring_entrypoints"], 1)
            self.assertEqual(graph["spring"]["entrypoints"][0]["method"], "GET")
            self.assertEqual(graph["spring"]["entrypoints"][0]["path"], "/users/{id}")
            self.assertIn(
                {
                    "from": "com.example.UserController.getUser",
                    "to": "com.example.UserService.findUser",
                    "line": 17,
                    "call": "findUser",
                    "resolver": "javalang",
                },
                graph["edges"],
            )

            chain = trace_static_call_chain(str(repo), "findUser")
            self.assertEqual(chain["entrypoints"][0]["handler"], "com.example.UserController.getUser")


if __name__ == "__main__":
    unittest.main()
