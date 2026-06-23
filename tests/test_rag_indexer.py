import tempfile
import unittest
from pathlib import Path

from backend.rag.indexer import _collect_documents


class RagIndexerTests(unittest.TestCase):
    def test_python_ast_aware_chunks_keep_function_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "service.py").write_text(
                "import os\n\n"
                "class UserService:\n"
                "    def get_user(self, user_id):\n"
                "        return load_user(user_id)\n\n"
                "def load_user(user_id):\n"
                "    return {'id': user_id}\n",
                encoding="utf-8",
            )

            docs = _collect_documents(repo)
            symbols = {doc["symbol"] for doc in docs}
            self.assertIn("UserService.get_user", symbols)
            self.assertIn("load_user", symbols)

            method_doc = next(doc for doc in docs if doc["symbol"] == "UserService.get_user")
            self.assertEqual(method_doc["chunk_type"], "method")
            self.assertIn("import os", method_doc["content"])
            self.assertIn("class UserService:", method_doc["content"])
            self.assertIn("def get_user", method_doc["content"])

    def test_java_ast_aware_chunks_keep_class_and_import_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "UserController.java").write_text(
                """
package com.example;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class UserController {
    private UserService userService;

    @GetMapping("/users")
    public String getUser() {
        return userService.findUser();
    }
}
""",
                encoding="utf-8",
            )

            docs = _collect_documents(repo)
            method_doc = next(doc for doc in docs if doc["symbol"] == "UserController.getUser")
            self.assertEqual(method_doc["chunk_type"], "method")
            self.assertIn("package com.example;", method_doc["content"])
            self.assertIn("@RestController", method_doc["content"])
            self.assertIn("public class UserController", method_doc["content"])
            self.assertIn("public String getUser()", method_doc["content"])


if __name__ == "__main__":
    unittest.main()
