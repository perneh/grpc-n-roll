from __future__ import annotations

import time
from itertools import count

import grpc

from tests.support.proto import ensure_compiled

ensure_compiled()

import users_pb2
import users_pb2_grpc


class UserServicer(users_pb2_grpc.UserServiceServicer):
    """In-memory user store used by the readable REST-style tests."""

    def __init__(self) -> None:
        self._users: dict[str, users_pb2.User] = {}
        self._ids = count(1)

    def GetUser(self, request, context):
        self._echo_request_id(context)
        user = self._users.get(request.id)
        if user is None:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details(f"User {request.id!r} was not found")
            return users_pb2.User()
        return user

    def ListUsers(self, request, context):
        for user in self._users.values():
            if request.name_prefix and not user.name.startswith(request.name_prefix):
                continue
            yield user

    def CreateUser(self, request, context):
        if not request.name:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details("name is required")
            return users_pb2.User()
        return self._store(request.name, request.email)

    def UpdateUser(self, request, context):
        user = self._users.get(request.id)
        if user is None:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details(f"User {request.id!r} was not found")
            return users_pb2.User()
        if request.name:
            user.name = request.name
        if request.email:
            user.email = request.email
        return user

    def DeleteUser(self, request, context):
        if request.id not in self._users:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details(f"User {request.id!r} was not found")
            return users_pb2.DeleteUserResponse()
        del self._users[request.id]
        return users_pb2.DeleteUserResponse()

    def ImportUsers(self, request_iterator, context):
        created = 0
        for request in request_iterator:
            if not request.name:
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details("name is required")
                return users_pb2.ImportSummary(created=created)
            self._store(request.name, request.email)
            created += 1
        return users_pb2.ImportSummary(created=created)

    def Echo(self, request_iterator, context):
        for message in request_iterator:
            yield message

    def Delay(self, request, context):
        time.sleep(request.seconds)
        return users_pb2.User(id="0", name="slow")

    def _store(self, name: str, email: str) -> users_pb2.User:
        user_id = str(next(self._ids))
        user = users_pb2.User(id=user_id, name=name, email=email)
        self._users[user_id] = user
        return user

    @staticmethod
    def _echo_request_id(context) -> None:
        for key, value in context.invocation_metadata():
            if key == "x-request-id":
                context.set_trailing_metadata((("x-request-id", value),))
                return
