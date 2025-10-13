from .constants import MISSING

try:
    from collections.abc import Callable
    from typing import Any, TypeAlias

    from .constants import MissingLiteral

    DefaultFactory: TypeAlias = Callable[[], Any]
except ImportError:
    pass


class FrozenInstanceError(AttributeError):
    """Exception raised when attempting to mutate a frozen dataclass instance."""

    pass


def field(
    *,
    default: Any | MissingLiteral = MISSING,
    default_factory: DefaultFactory | MissingLiteral = MISSING,
    init: bool = True,
    repr: bool = True,
    hash: bool | None = None,
    compare: bool = True,
) -> "Field":
    """Function for explicitly declaring a field."""
    return Field(
        default=default,
        default_factory=default_factory,
        init=init,
        repr=repr,
        hash=hash,
        compare=compare,
    )


class Field:
    """
    Internal representation of a field provided by introspection routines.
    Users should not directly instantiate this class.
    """

    name: str
    type: type = object
    default: Any | MissingLiteral
    default_factory: DefaultFactory | MissingLiteral
    init: bool
    repr: bool
    hash: bool | None
    compare: bool

    init_only: bool

    def __init__(
        self,
        name: str = "<UNSET>",
        default: Any = MISSING,
        default_factory: DefaultFactory | MissingLiteral = MISSING,
        init: bool = True,
        repr: bool = True,
        hash: bool | None = None,
        compare: bool = True,
        init_only: bool = False,
    ) -> None:
        self.name = name
        self.default = default
        self.default_factory = default_factory
        self.init = init
        self.repr = repr
        self.hash = hash
        self.compare = compare
        self.init_only = init_only

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Field):
            return self.name == other.name
        return False

    def __repr__(self) -> str:
        return f"Field({self.name!r}, {self.default!r})"

    @property
    def _name(self) -> str:
        return f"_{self.name}"

    @property
    def default_value_name(self) -> str:
        """Name to use for storing the default value as a global."""
        return f"__dataclass_default_{self.name}"

    @property
    def contributes_to_hash(self) -> bool:
        """True if this field should contribute to generated __hash__() method."""
        if self.hash is None:
            return self.compare
        return self.hash
