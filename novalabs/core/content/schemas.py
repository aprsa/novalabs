"""
Pydantic schemas for validating lab content TOML files.

These schemas define the expected structure of:
- lab.toml (main lab configuration)
- pre_quiz.toml / post_quiz.toml (quiz questions)
- exercise.toml (exercise definitions)
"""

from typing import Optional, List, Any
from pydantic import BaseModel, Field, field_validator


class ExerciseReference(BaseModel):
    """Reference to an exercise in lab.toml."""
    dir: str = Field(description="Exercise directory name (e.g., '01_polaris_latitude')")
    max_points: float = Field(default=20.0, ge=0)


class BriefingConfig(BaseModel):
    """Briefing configuration."""
    file: str = Field(default="briefing.md", description="Path to briefing markdown file")


class QuizReference(BaseModel):
    """Reference to a quiz file."""
    file: str = Field(description="Path to quiz TOML file")


class UIConfig(BaseModel):
    """
    UI configuration for the lab.

    Allows explicit specification of a custom UI class. If not provided,
    the framework will look for a conventional ui.py file in the lab
    directory, and fall back to BaseLabUI if none is found.

    Example:
        [ui]
        class = "mylab.ui:MyCustomLabUI"
    """
    class_path: Optional[str] = Field(
        default=None,
        alias="class",
        description="Python import path to custom UI class (e.g., 'mylab.ui:MyLabUI')"
    )

    model_config = {"populate_by_name": True}


class LabMetadata(BaseModel):
    """Lab metadata section of lab.toml."""
    slug: str = Field(min_length=1, max_length=50)
    title: str = Field(min_length=1, max_length=200)
    description: Optional[str] = None
    version: str = Field(default="1.0.0")
    passing_score: int = Field(default=8, ge=1, le=10)


class LabConfig(BaseModel):
    """
    Complete lab configuration from lab.toml.

    Example:
        [lab]
        slug = "celestial_sphere"
        title = "The Celestial Sphere"
        passing_score = 8

        [briefing]
        file = "briefing.md"

        [pre_quiz]
        file = "pre_quiz.toml"

        [post_quiz]
        file = "post_quiz.toml"

        [ui]
        class = "mylab.ui:MyCustomLabUI"  # Optional

        [[exercises]]
        dir = "01_polaris_latitude"
        max_points = 20
    """
    lab: LabMetadata
    briefing: BriefingConfig = Field(default_factory=lambda: BriefingConfig())
    pre_quiz: QuizReference = Field(default_factory=lambda: QuizReference(file="pre_quiz.toml"))
    post_quiz: QuizReference = Field(default_factory=lambda: QuizReference(file="post_quiz.toml"))
    ui: UIConfig = Field(default_factory=UIConfig)
    exercises: List[ExerciseReference] = Field(default_factory=list)


class QuestionConfig(BaseModel):
    """
    Single quiz question.

    Example:
        [[questions]]
        text = "What causes the apparent daily motion of stars?"
        options = [
            "Earth's rotation on its axis",
            "Earth's revolution around the Sun",
            "The Moon's gravitational pull",
            "Stars actually moving through space"
        ]
        correct = 0
    """
    text: str = Field(min_length=1)
    options: List[str] = Field(min_length=2, max_length=6)
    correct: int = Field(ge=0)

    @field_validator('correct')
    @classmethod
    def correct_in_range(cls, v: int, info) -> int:
        # Note: We can't access 'options' here easily in Pydantic v2
        # Validation will be done at load time
        return v


class QuizMetadata(BaseModel):
    """Quiz metadata section."""
    instructions: Optional[str] = None


class QuizConfig(BaseModel):
    """
    Complete quiz configuration from pre_quiz.toml or post_quiz.toml.

    Example:
        [quiz]
        instructions = "Answer based on the Mission Briefing."

        [[questions]]
        text = "..."
        options = [...]
        correct = 0
    """
    quiz: QuizMetadata = Field(default_factory=QuizMetadata)
    questions: List[QuestionConfig] = Field(min_length=1)

    @field_validator('questions')
    @classmethod
    def validate_questions(cls, v: List[QuestionConfig]) -> List[QuestionConfig]:
        for i, q in enumerate(v):
            if q.correct >= len(q.options):
                raise ValueError(
                    f"Question {i+1}: correct index {q.correct} out of range "
                    f"(only {len(q.options)} options)"
                )
        return v


class DataColumnConfig(BaseModel):
    """Column definition for data_entry task."""
    name: str
    unit: Optional[str] = None
    editable: bool = True
    values: Optional[List[Any]] = None  # Pre-filled values if not editable


class TaskConfig(BaseModel):
    """
    Individual task within an exercise.

    Example (data_entry):
        [[tasks]]
        number = 1
        type = "data_entry"
        prompt = "Record the altitude of Polaris at each latitude:"

        [[tasks.columns]]
        name = "Latitude"
        unit = "°"
        editable = false
        values = [0, 20, 40, 60, 90]

        [[tasks.columns]]
        name = "Polaris Altitude"
        unit = "°"
        editable = true

    Example (short_answer):
        [[tasks]]
        number = 2
        type = "short_answer"
        prompt = "What pattern do you notice?"
    """
    number: int = Field(ge=1)
    type: str = Field(pattern="^(data_entry|short_answer|long_answer|numeric|selection)$")
    prompt: str = Field(min_length=1)

    # Type-specific configuration
    columns: Optional[List[DataColumnConfig]] = None  # For data_entry
    options: Optional[List[str]] = None  # For selection
    unit: Optional[str] = None  # For numeric
    min_value: Optional[float] = None  # For numeric
    max_value: Optional[float] = None  # For numeric

    # Extension point for custom task configuration
    # Labs can add arbitrary configuration here for custom task types
    extra: Optional[dict] = Field(default=None, description="Custom configuration for extended task types")


class ExerciseMetadata(BaseModel):
    """Exercise metadata section."""
    number: int = Field(ge=1)
    title: str = Field(min_length=1, max_length=200)
    objective: Optional[str] = None


class ExerciseFiles(BaseModel):
    """References to external markdown files."""
    instructions_file: str = Field(default="instructions.md")
    prediction_file: Optional[str] = Field(default="prediction.md")
    conclusion_file: Optional[str] = Field(default="conclusion.md")


class ExerciseConfig(BaseModel):
    """
    Complete exercise configuration from exercise.toml.

    Example:
        [exercise]
        number = 1
        title = "Polaris and Latitude"
        objective = "Discover the relationship..."

        [files]
        instructions_file = "instructions.md"
        prediction_file = "prediction.md"
        conclusion_file = "conclusion.md"

        [[tasks]]
        number = 1
        type = "data_entry"
        ...
    """
    exercise: ExerciseMetadata
    files: ExerciseFiles = Field(default_factory=ExerciseFiles)
    tasks: List[TaskConfig] = Field(default_factory=list)

    # Extension point for custom exercise configuration
    # Labs can add arbitrary configuration here
    extra: Optional[dict] = Field(default=None, description="Custom configuration for extended exercises")

    @field_validator('tasks')
    @classmethod
    def validate_task_numbers(cls, v: List[TaskConfig]) -> List[TaskConfig]:
        numbers = [t.number for t in v]
        if len(numbers) != len(set(numbers)):
            raise ValueError("Duplicate task numbers found")
        return v
