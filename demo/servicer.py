"""UserService backed by the shared lab store, with live RPC events."""

from __future__ import annotations

import logging
import time
from typing import Any

import grpc

from demo.state import publish

from tests.support.proto import ensure_compiled

ensure_compiled()

import users_pb2
import users_pb2_grpc

logger = logging.getLogger(__name__)


class UserServicer(users_pb2_grpc.UserServiceServicer):
    def __init__(self, state: dict[str, Any]) -> None:
        self._state = state

    def GetUser(self, request, context):
        self._echo_request_id(context)
        with self._state["lock"]:
            user = self._state["users"].get(request.id)
        if user is None:
            publish(
                self._state,
                method="GET",
                path="/users.UserService/GetUser",
                grpc_status=grpc.StatusCode.NOT_FOUND,
                detail=f"id={request.id}",
            )
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details(f"User {request.id!r} was not found")
            return users_pb2.User()
        publish(
            self._state,
            method="GET",
            path="/users.UserService/GetUser",
            grpc_status=grpc.StatusCode.OK,
            detail=user.name,
        )
        return user

    def ListUsers(self, request, context):
        with self._state["lock"]:
            users = list(self._state["users"].values())
        matched = []
        for user in users:
            if request.name_prefix and not user.name.startswith(request.name_prefix):
                continue
            matched.append(user)
            yield user
        publish(
            self._state,
            method="GET",
            path="/users.UserService/ListUsers",
            grpc_status=grpc.StatusCode.OK,
            detail=f"{len(matched)} user(s)",
        )

    def CreateUser(self, request, context):
        if not request.name:
            publish(
                self._state,
                method="POST",
                path="/users.UserService/CreateUser",
                grpc_status=grpc.StatusCode.INVALID_ARGUMENT,
                detail="name is required",
            )
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details("name is required")
            return users_pb2.User()
        user = self._store(request.name, request.email)
        publish(
            self._state,
            method="POST",
            path="/users.UserService/CreateUser",
            grpc_status=grpc.StatusCode.OK,
            detail=user.name,
        )
        return user

    def UpdateUser(self, request, context):
        with self._state["lock"]:
            user = self._state["users"].get(request.id)
            if user is not None:
                if request.name:
                    user.name = request.name
                if request.email:
                    user.email = request.email
        if user is None:
            publish(
                self._state,
                method="PUT",
                path="/users.UserService/UpdateUser",
                grpc_status=grpc.StatusCode.NOT_FOUND,
                detail=f"id={request.id}",
            )
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details(f"User {request.id!r} was not found")
            return users_pb2.User()
        publish(
            self._state,
            method="PUT",
            path="/users.UserService/UpdateUser",
            grpc_status=grpc.StatusCode.OK,
            detail=user.name,
        )
        return user

    def DeleteUser(self, request, context):
        with self._state["lock"]:
            user = self._state["users"].pop(request.id, None)
        if user is None:
            publish(
                self._state,
                method="DELETE",
                path="/users.UserService/DeleteUser",
                grpc_status=grpc.StatusCode.NOT_FOUND,
                detail=f"id={request.id}",
            )
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details(f"User {request.id!r} was not found")
            return users_pb2.DeleteUserResponse()
        publish(
            self._state,
            method="DELETE",
            path="/users.UserService/DeleteUser",
            grpc_status=grpc.StatusCode.OK,
            detail=user.name,
        )
        return users_pb2.DeleteUserResponse()

    def ImportUsers(self, request_iterator, context):
        created = 0
        for request in request_iterator:
            if not request.name:
                publish(
                    self._state,
                    method="POST",
                    path="/users.UserService/ImportUsers",
                    grpc_status=grpc.StatusCode.INVALID_ARGUMENT,
                    detail="name is required",
                )
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details("name is required")
                return users_pb2.ImportSummary(created=created)
            self._store(request.name, request.email)
            created += 1
        publish(
            self._state,
            method="POST",
            path="/users.UserService/ImportUsers",
            grpc_status=grpc.StatusCode.OK,
            detail=f"created={created}",
        )
        return users_pb2.ImportSummary(created=created)

    def Echo(self, request_iterator, context):
        count = 0
        for message in request_iterator:
            count += 1
            yield message
        publish(
            self._state,
            method="POST",
            path="/users.UserService/Echo",
            grpc_status=grpc.StatusCode.OK,
            detail=f"{count} message(s)",
        )

    def Delay(self, request, context):
        time.sleep(request.seconds)
        publish(
            self._state,
            method="GET",
            path="/users.UserService/Delay",
            grpc_status=grpc.StatusCode.OK,
            detail=f"{request.seconds}s",
        )
        return users_pb2.User(id="0", name="slow")

    def _store(self, name: str, email: str) -> users_pb2.User:
        with self._state["lock"]:
            user_id = str(next(self._state["ids"]))
            user = users_pb2.User(id=user_id, name=name, email=email)
            self._state["users"][user_id] = user
        logger.debug("Stored user id=%s name=%s", user_id, name)
        return user

    @staticmethod
    def _echo_request_id(context) -> None:
        for key, value in context.invocation_metadata():
            if key == "x-request-id":
                context.set_trailing_metadata((("x-request-id", value),))
                return
