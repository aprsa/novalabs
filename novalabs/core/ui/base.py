"""
Base UI class for NovaLabs labs.

BaseLabUI provides the presentation layer for labs, rendering NiceGUI
components for all phases of lab execution. It is designed to work
out-of-the-box for any lab defined via TOML specs, while allowing
fine-grained customization through method overrides.

Method Hierarchy (all overridable):
    render()                      # Top-level entry point (full control)
    ├── sidebar()                 # Progress sidebar
    │   ├── lab_title()
    │   ├── phase_indicators()
    │   └── exercise_list()
    └── main_content()            # Main content area
        └── phase_content()       # Routes to current phase
            ├── briefing()
            ├── pre_quiz() → quiz()
            ├── exercises()
            ├── post_quiz() → quiz()
            └── completion()

Usage:
    # Default usage (via lab page)
    lab_logic = BaseLab(user_id=123, lab=lab_model)
    await lab_logic.init()
    lab_ui = BaseLabUI(lab_logic)
    await lab_ui.render()
    
    # Custom UI (override specific methods)
    class MyLabUI(BaseLabUI):
        async def briefing_content(self) -> None:
            # Custom briefing with visualization
            with ui.row():
                ui.markdown(self.lab.lab.briefing_content)
                MyCustomWidget()
"""

import logging
import traceback
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from nicegui import ui

from ..models import Exercise, ExerciseTask, AdminNotification

if TYPE_CHECKING:
    from ..labs.base import BaseLab
    from ..managers.quiz import QuizResult

logger = logging.getLogger(__name__)


class BaseLabUI:
    """
    Presentation layer for NovaLabs labs.
    
    Renders all lab phases using NiceGUI components. Works with any lab
    that provides TOML specs and content files. Override methods for
    custom presentations.
    
    Attributes:
        lab: The BaseLab logic layer instance
        phase: Current phase ('briefing', 'pre_quiz', 'exercises', 'post_quiz', 'complete')
        current_exercise_index: Index of current exercise when in exercises phase
    """
    
    def __init__(self, lab: 'BaseLab'):
        """
        Initialize the UI layer.
        
        Args:
            lab: The BaseLab (or subclass) instance providing logic layer
        """
        self.lab = lab
        
        # State
        self.phase: str = 'briefing'
        self.current_exercise_index: int = 0
        
        # UI containers (set during render)
        self.main_container: Optional[ui.column] = None
        self.sidebar_container: Optional[ui.column] = None
        
        # Quiz state
        self._quiz_answers: Dict[int, Optional[int]] = {}
        self._current_quiz_phase: str = 'pre'
        self._quiz_questions: List = []
    
    # =========================================================================
    # TOP-LEVEL ENTRY POINT
    # =========================================================================
    
    async def render(self) -> None:
        """
        Main entry point for rendering the lab UI.
        
        Override this method for complete control over the entire UI structure.
        Default implementation creates a two-column layout with sidebar and
        main content area.
        """
        # Browser back button warning
        ui.add_head_html('''
            <script>
            window.addEventListener('beforeunload', function(e) {
                e.preventDefault();
                e.returnValue = 'You have unsaved progress. Are you sure you want to leave?';
                return e.returnValue;
            });
            </script>
        ''')
        
        # Start the lab if not already started
        await self.lab.on_start()
        
        with ui.row().classes('w-full h-full gap-0'):
            await self.sidebar()
            await self.main_content()
    
    # =========================================================================
    # STRUCTURAL COMPONENTS
    # =========================================================================
    
    async def sidebar(self) -> None:
        """
        Render the progress sidebar.
        
        Override for custom sidebar layout.
        """
        with ui.column().classes('w-64 min-w-64 bg-gray-100 p-4 h-screen overflow-auto') as container:
            self.sidebar_container = container
            await self.lab_title()
            ui.separator().classes('my-4')
            await self.phase_indicators()
            ui.separator().classes('my-4')
            await self.exercise_list()
    
    async def main_content(self) -> None:
        """
        Render the main content area.
        
        Override for custom main area layout.
        """
        with ui.column().classes('flex-1 p-6 overflow-auto h-screen') as container:
            self.main_container = container
            await self.phase_content()
    
    # =========================================================================
    # SIDEBAR COMPONENTS
    # =========================================================================
    
    async def lab_title(self) -> None:
        """Render the lab title in sidebar."""
        ui.label(self.lab.lab.title).classes('text-xl font-bold')
        if self.lab.lab.description:
            ui.label(self.lab.lab.description).classes('text-sm text-gray-600 mt-1')
    
    async def phase_indicators(self) -> None:
        """Render phase completion indicators in sidebar."""
        summary = await self.lab.get_progress_summary()
        
        phases = [
            ('Briefing', 'briefing', summary.briefing_complete),
            ('Pre-Quiz', 'pre_quiz', summary.pre_quiz_passed),
            ('Exercises', 'exercises', summary.exercises_submitted),
            ('Post-Quiz', 'post_quiz', summary.post_quiz_passed),
        ]
        
        for label, phase_key, complete in phases:
            is_current = (self.phase == phase_key)
            
            if complete:
                icon = '✓'
                color = 'text-green-600'
            elif is_current:
                icon = '●'
                color = 'text-blue-600 font-bold'
            else:
                icon = '○'
                color = 'text-gray-400'
            
            ui.label(f'{icon} {label}').classes(color)
    
    async def exercise_list(self) -> None:
        """Render exercise list in sidebar."""
        ui.label('Exercises').classes('font-bold mb-2')
        
        statuses = await self.lab.get_exercise_statuses()
        
        if not statuses:
            ui.label('No exercises defined').classes('text-gray-400 text-sm italic')
            return
        
        for i, status in enumerate(statuses):
            if status.is_complete:
                icon = '✓'
                color = 'text-green-600'
            elif status.is_started:
                icon = '◐'
                color = 'text-yellow-600'
            else:
                icon = '○'
                color = 'text-gray-400'
            
            is_current = (self.phase == 'exercises' and i == self.current_exercise_index)
            weight = 'font-bold' if is_current else ''
            
            label = f'{icon} {status.exercise_number}. {status.title}'
            ui.label(label).classes(f'{color} text-sm {weight}')
    
    # =========================================================================
    # PHASE ROUTING
    # =========================================================================
    
    async def phase_content(self) -> None:
        """
        Route to the appropriate phase renderer.
        
        Override to add custom phases or change routing logic.
        """
        renderers = {
            'briefing': self.briefing,
            'pre_quiz': self.pre_quiz,
            'exercises': self.exercises,
            'post_quiz': self.post_quiz,
            'complete': self.completion,
        }
        
        renderer = renderers.get(self.phase, self.briefing)
        await renderer()
    
    # =========================================================================
    # BRIEFING PHASE
    # =========================================================================
    
    async def briefing(self) -> None:
        """
        Render the briefing phase.
        
        Override for custom briefing layout.
        """
        await self.briefing_header()
        await self.briefing_content()
        await self.briefing_navigation()
    
    async def briefing_header(self) -> None:
        """Render briefing header."""
        ui.label('Mission Briefing').classes('text-2xl font-bold mb-4')
    
    async def briefing_content(self) -> None:
        """Render briefing content (markdown)."""
        content = self.lab.lab.briefing_content or "No briefing content available."
        ui.markdown(content).classes('prose max-w-none')
    
    async def briefing_navigation(self) -> None:
        """Render briefing navigation button."""
        ui.button(
            'Continue to Pre-Quiz →',
            on_click=self._advance_to_pre_quiz
        ).classes('mt-6')
    
    async def _advance_to_pre_quiz(self) -> None:
        """Handle transition from briefing to pre-quiz."""
        await self._safe_execute(
            self.lab.on_briefing_complete(),
            'briefing_complete'
        )
        self.phase = 'pre_quiz'
        await self._refresh_ui()
    
    # =========================================================================
    # QUIZ PHASES (PRE AND POST)
    # =========================================================================
    
    async def pre_quiz(self) -> None:
        """Render pre-quiz phase."""
        await self.quiz('pre')
    
    async def post_quiz(self) -> None:
        """Render post-quiz phase."""
        await self.quiz('post')
    
    async def quiz(self, phase: str) -> None:
        """
        Render a quiz (pre or post).
        
        Args:
            phase: 'pre' or 'post'
        """
        self._current_quiz_phase = phase
        self._quiz_questions = await self.lab.get_quiz_questions(phase)
        attempt_number = await self.lab.get_quiz_attempt_number(phase)
        
        # Track quiz start
        await self._safe_execute(
            self.lab.on_quiz_start(phase, attempt_number),
            f'{phase}_quiz_start'
        )
        
        # Initialize answer storage
        self._quiz_answers = {i: None for i in range(len(self._quiz_questions))}
        
        await self.quiz_header(phase, attempt_number)
        
        for i, question in enumerate(self._quiz_questions):
            await self.quiz_question(question, i)
        
        await self.quiz_navigation(phase)
    
    async def quiz_header(self, phase: str, attempt_number: int) -> None:
        """Render quiz header."""
        title = 'Pre-Lab Quiz' if phase == 'pre' else 'Post-Lab Quiz'
        ui.label(title).classes('text-2xl font-bold mb-2')
        
        if attempt_number > 1:
            ui.label(f'Attempt {attempt_number}').classes('text-gray-500 mb-4')
        else:
            ui.label('Answer all questions and submit.').classes('text-gray-500 mb-4')
    
    async def quiz_question(self, question, index: int) -> None:
        """
        Render a single quiz question.
        
        Args:
            question: Question model instance
            index: Question index (0-based)
        """
        with ui.card().classes('w-full mb-4 p-4'):
            ui.label(f'{index + 1}. {question.question_text}').classes('font-medium mb-3')
            
            options = {j: opt for j, opt in enumerate(question.options)}
            
            radio = ui.radio(
                options=options,
                on_change=lambda e, idx=index: self._quiz_answers.__setitem__(idx, e.value)
            ).props('dense')
    
    async def quiz_navigation(self, phase: str) -> None:
        """Render quiz navigation buttons."""
        with ui.row().classes('mt-6 gap-4'):
            ui.button(
                '← Return to Briefing',
                on_click=self._return_to_briefing
            ).props('flat')
            
            ui.button(
                'Submit Answers',
                on_click=lambda: self._submit_quiz(phase)
            )
    
    async def _submit_quiz(self, phase: str) -> None:
        """Handle quiz submission."""
        # Check all questions answered
        if None in self._quiz_answers.values():
            ui.notify('Please answer all questions before submitting.', type='warning')
            return
        
        answers = [self._quiz_answers[i] for i in range(len(self._quiz_questions))]
        attempt_number = await self.lab.get_quiz_attempt_number(phase)
        
        try:
            result = await self.lab.submit_quiz_answers(phase, answers, self._quiz_questions)
            
            await self._safe_execute(
                self.lab.on_quiz_complete(phase, attempt_number),
                f'{phase}_quiz_complete'
            )
            
            if result.passed:
                ui.notify(
                    f'Passed! {result.score}/{result.total} correct. '
                    f'Points earned: {result.cumulative_points:.1f}',
                    type='positive'
                )
                
                if phase == 'pre':
                    self.phase = 'exercises'
                    self.current_exercise_index = 0
                else:
                    await self._safe_execute(
                        self.lab.on_lab_complete(),
                        'lab_complete'
                    )
                    self.phase = 'complete'
                
                await self._refresh_ui()
            else:
                # Show feedback
                await self._show_quiz_feedback(result)
                
        except Exception as e:
            await self._report_error(e, f'quiz_submit_{phase}')
            ui.notify('An error occurred while submitting. Please try again.', type='negative')
    
    async def _show_quiz_feedback(self, result: 'QuizResult') -> None:
        """Show quiz feedback with correct/incorrect indicators."""
        if self.main_container is None:
            return
        
        self.main_container.clear()
        
        with self.main_container:
            ui.label('Please review and try again').classes('text-xl font-bold mb-2 text-orange-600')
            ui.label(f'{result.score}/{result.total} correct').classes('text-gray-600 mb-4')
            
            for i, question in enumerate(self._quiz_questions):
                is_correct = i not in result.incorrect_indices
                
                border_color = 'border-green-500' if is_correct else 'border-red-500'
                icon = '✓' if is_correct else '✗'
                text_color = 'text-green-600' if is_correct else 'text-red-600'
                
                with ui.card().classes(f'w-full mb-4 p-4 border-2 {border_color}'):
                    ui.label(f'{icon} {i + 1}. {question.question_text}').classes(f'font-medium mb-3 {text_color}')
                    
                    # Keep correct answers, clear incorrect ones
                    initial_value = self._quiz_answers[i] if is_correct else None
                    if not is_correct:
                        self._quiz_answers[i] = None
                    
                    options = {j: opt for j, opt in enumerate(question.options)}
                    
                    ui.radio(
                        options=options,
                        value=initial_value,
                        on_change=lambda e, idx=i: self._quiz_answers.__setitem__(idx, e.value)
                    ).props('dense')
            
            with ui.row().classes('mt-6 gap-4'):
                ui.button(
                    '← Return to Briefing',
                    on_click=self._return_to_briefing
                ).props('flat')
                
                ui.button(
                    'Try Again',
                    on_click=lambda: self._submit_quiz(self._current_quiz_phase)
                )
    
    async def _return_to_briefing(self) -> None:
        """Return to briefing phase."""
        self.phase = 'briefing'
        await self._refresh_ui()
    
    # =========================================================================
    # EXERCISES PHASE
    # =========================================================================
    
    async def exercises(self) -> None:
        """
        Render the exercises phase.
        
        Shows one exercise at a time with prev/next navigation.
        """
        exercise_list = await self.lab.get_exercises()
        
        if not exercise_list:
            ui.label('No exercises defined for this lab.').classes('text-gray-500 italic')
            await self.exercises_navigation_no_exercises()
            return
        
        # Ensure index is valid
        if self.current_exercise_index >= len(exercise_list):
            self.current_exercise_index = len(exercise_list) - 1
        
        exercise = exercise_list[self.current_exercise_index]
        
        # Track exercise entry
        await self._safe_execute(
            self.lab.on_exercise_enter(exercise.id),
            f'exercise_enter_{exercise.id}'
        )
        
        await self.exercise_header(exercise)
        await self.exercise_content(exercise)
        await self.exercise_navigation(exercise_list)
    
    async def exercises_navigation_no_exercises(self) -> None:
        """Render navigation when there are no exercises."""
        ui.button(
            'Continue to Post-Quiz →',
            on_click=self._advance_to_post_quiz
        ).classes('mt-6')
    
    async def exercise_header(self, exercise: Exercise) -> None:
        """Render exercise header."""
        ui.label(
            f'Exercise {exercise.exercise_number}: {exercise.title}'
        ).classes('text-2xl font-bold mb-2')
        
        if exercise.objective:
            ui.label(exercise.objective).classes('text-gray-600 mb-4')
    
    async def exercise_content(self, exercise: Exercise) -> None:
        """
        Render exercise content (instructions, prediction, tasks, conclusion).
        
        Override for custom exercise layout.
        """
        # Instructions
        if exercise.instructions:
            with ui.expansion('Instructions', value=True).classes('w-full mb-4'):
                ui.markdown(exercise.instructions).classes('prose max-w-none')
        
        # Prediction section
        if exercise.prediction_prompt:
            await self.prediction_section(exercise)
        
        # Tasks
        tasks = await self.lab.get_exercise_tasks(exercise.id)
        for task in tasks:
            await self.task(task)
        
        # Conclusion section
        if exercise.conclusion_prompt:
            await self.conclusion_section(exercise)
    
    async def prediction_section(self, exercise: Exercise) -> None:
        """Render the prediction section of an exercise."""
        with ui.card().classes('w-full mb-4 p-4'):
            ui.label('Prediction').classes('font-bold mb-2')
            ui.markdown(exercise.prediction_prompt).classes('prose max-w-none mb-3')
            
            response = await self.lab.get_exercise_response(exercise.id)
            initial = response.prediction_text if response else ''
            
            prediction = ui.textarea(
                value=initial,
                placeholder='Write your prediction here...'
            ).classes('w-full').props('rows=4')
            
            # Auto-save on blur
            prediction.on(
                'blur',
                lambda e=exercise: self._save_prediction(e.id, prediction.value)
            )
    
    async def _save_prediction(self, exercise_id: int, text: str) -> None:
        """Save prediction with error handling."""
        await self._safe_execute(
            self.lab.save_prediction(exercise_id, text),
            f'save_prediction_{exercise_id}'
        )
    
    async def conclusion_section(self, exercise: Exercise) -> None:
        """Render the conclusion section of an exercise."""
        with ui.card().classes('w-full mb-4 p-4'):
            ui.label('Conclusion').classes('font-bold mb-2')
            ui.markdown(exercise.conclusion_prompt).classes('prose max-w-none mb-3')
            
            response = await self.lab.get_exercise_response(exercise.id)
            initial = response.conclusion_text if response else ''
            
            conclusion = ui.textarea(
                value=initial,
                placeholder='Write your conclusion here...'
            ).classes('w-full').props('rows=4')
            
            # Auto-save on blur
            conclusion.on(
                'blur',
                lambda e=exercise: self._save_conclusion(e.id, conclusion.value)
            )
    
    async def _save_conclusion(self, exercise_id: int, text: str) -> None:
        """Save conclusion with error handling."""
        await self._safe_execute(
            self.lab.save_conclusion(exercise_id, text),
            f'save_conclusion_{exercise_id}'
        )
    
    async def task(self, task: ExerciseTask) -> None:
        """
        Render a single task.
        
        Override for custom task types.
        """
        with ui.card().classes('w-full mb-4 p-4'):
            ui.label(f'Task {task.task_number}').classes('font-bold mb-2')
            ui.markdown(task.prompt).classes('prose max-w-none mb-3')
            
            task_renderers = {
                'short_answer': self.short_answer_task,
                'long_answer': self.long_answer_task,
                'numeric': self.numeric_task,
                'selection': self.selection_task,
                'data_entry': self.data_entry_task,
            }
            
            renderer = task_renderers.get(task.task_type)
            if renderer:
                await renderer(task)
            else:
                ui.label(f'Unknown task type: {task.task_type}').classes('text-red-500')
    
    async def short_answer_task(self, task: ExerciseTask) -> None:
        """Render a short answer task."""
        response = await self.lab.get_task_response(task.id)
        initial = response.response_data.get('text', '') if response else ''
        
        inp = ui.input(
            value=initial,
            placeholder='Your answer...'
        ).classes('w-full')
        
        inp.on(
            'blur',
            lambda t=task: self._save_task_response(t.id, {'text': inp.value})
        )
    
    async def long_answer_task(self, task: ExerciseTask) -> None:
        """Render a long answer task."""
        response = await self.lab.get_task_response(task.id)
        initial = response.response_data.get('text', '') if response else ''
        
        textarea = ui.textarea(
            value=initial,
            placeholder='Your answer...'
        ).classes('w-full').props('rows=5')
        
        textarea.on(
            'blur',
            lambda t=task: self._save_task_response(t.id, {'text': textarea.value})
        )
    
    async def numeric_task(self, task: ExerciseTask) -> None:
        """Render a numeric input task."""
        config = task.config or {}
        response = await self.lab.get_task_response(task.id)
        initial = response.response_data.get('value') if response else None
        
        with ui.row().classes('items-center'):
            inp = ui.number(
                value=initial,
                min=config.get('min_value'),
                max=config.get('max_value'),
            ).classes('w-32')
            
            if config.get('unit'):
                ui.label(config['unit']).classes('ml-2')
        
        inp.on(
            'blur',
            lambda t=task: self._save_task_response(t.id, {'value': inp.value})
        )
    
    async def selection_task(self, task: ExerciseTask) -> None:
        """Render a selection (radio) task."""
        config = task.config or {}
        options = config.get('options', [])
        
        response = await self.lab.get_task_response(task.id)
        initial = response.response_data.get('selected_index') if response else None
        
        radio = ui.radio(
            options={i: opt for i, opt in enumerate(options)},
            value=initial,
        )
        
        radio.on(
            'change',
            lambda e, t=task: self._save_task_response(t.id, {'selected_index': e.value})
        )
    
    async def data_entry_task(self, task: ExerciseTask) -> None:
        """Render a data entry table task."""
        config = task.config or {}
        columns = config.get('columns', [])
        
        if not columns:
            ui.label('No columns configured for this task.').classes('text-red-500')
            return
        
        # Get existing response
        response = await self.lab.get_task_response(task.id)
        existing_rows = response.response_data.get('rows', []) if response else []
        
        # Determine number of rows
        num_rows = config.get('expected_rows', 5)
        for col in columns:
            if col.get('values'):
                num_rows = len(col['values'])
                break
        
        # Initialize rows if needed
        if not existing_rows:
            existing_rows = [[None] * len(columns) for _ in range(num_rows)]
        
        # Build table with input fields
        with ui.element('div').classes('overflow-x-auto'):
            with ui.element('table').classes('min-w-full'):
                # Header row
                with ui.element('thead'):
                    with ui.element('tr'):
                        for col in columns:
                            unit = f" ({col.get('unit', '')})" if col.get('unit') else ''
                            with ui.element('th').classes('px-4 py-2 text-left font-bold'):
                                ui.label(f"{col['name']}{unit}")
                
                # Data rows
                inputs: List[List[Any]] = []
                with ui.element('tbody'):
                    for i in range(num_rows):
                        row_inputs: List[Any] = []
                        with ui.element('tr').classes('border-t'):
                            for j, col in enumerate(columns):
                                with ui.element('td').classes('px-4 py-2'):
                                    if col.get('editable', True) and not col.get('values'):
                                        # Editable cell
                                        val = ''
                                        if i < len(existing_rows) and j < len(existing_rows[i]):
                                            val = existing_rows[i][j] or ''
                                        inp = ui.input(value=str(val)).classes('w-24')
                                        row_inputs.append(inp)
                                    else:
                                        # Read-only cell (pre-filled)
                                        val = ''
                                        if col.get('values') and i < len(col['values']):
                                            val = col['values'][i]
                                        ui.label(str(val)).classes('py-2')
                                        row_inputs.append(val)
                        inputs.append(row_inputs)
        
        async def save_table():
            rows = []
            for row_inputs in inputs:
                row = []
                for inp in row_inputs:
                    if hasattr(inp, 'value'):
                        row.append(inp.value)
                    else:
                        row.append(inp)
                rows.append(row)
            
            await self._save_task_response(task.id, {'rows': rows})
            ui.notify('Data saved', type='positive')
        
        ui.button('Save Data', on_click=save_table).classes('mt-3')
    
    async def _save_task_response(self, task_id: int, data: dict) -> None:
        """Save task response with error handling."""
        await self._safe_execute(
            self.lab.save_task_response(task_id, data),
            f'save_task_{task_id}'
        )
    
    async def exercise_navigation(self, exercises: List[Exercise]) -> None:
        """Render exercise navigation buttons."""
        with ui.row().classes('mt-6 gap-4'):
            # Previous button
            if self.current_exercise_index > 0:
                ui.button(
                    '← Previous Exercise',
                    on_click=self._prev_exercise
                ).props('flat')
            
            # Next or Submit button
            if self.current_exercise_index < len(exercises) - 1:
                ui.button(
                    'Next Exercise →',
                    on_click=self._next_exercise
                )
            else:
                ui.button(
                    'Submit All & Continue to Post-Quiz →',
                    on_click=self._submit_exercises
                )
    
    async def _prev_exercise(self) -> None:
        """Navigate to previous exercise."""
        exercises = await self.lab.get_exercises()
        if self.current_exercise_index > 0:
            current = exercises[self.current_exercise_index]
            await self._safe_execute(
                self.lab.on_exercise_leave(current.id),
                f'exercise_leave_{current.id}'
            )
            
            self.current_exercise_index -= 1
            await self._refresh_ui()
    
    async def _next_exercise(self) -> None:
        """Navigate to next exercise."""
        exercises = await self.lab.get_exercises()
        if self.current_exercise_index < len(exercises) - 1:
            current = exercises[self.current_exercise_index]
            await self._safe_execute(
                self.lab.on_exercise_leave(current.id),
                f'exercise_leave_{current.id}'
            )
            
            self.current_exercise_index += 1
            await self._refresh_ui()
    
    async def _submit_exercises(self) -> None:
        """Submit all exercises and advance to post-quiz."""
        await self._safe_execute(
            self.lab.on_exercises_submit(),
            'exercises_submit'
        )
        
        self.phase = 'post_quiz'
        await self._refresh_ui()
    
    async def _advance_to_post_quiz(self) -> None:
        """Advance directly to post-quiz (when no exercises)."""
        await self._safe_execute(
            self.lab.on_exercises_submit(),
            'exercises_submit'
        )
        
        self.phase = 'post_quiz'
        await self._refresh_ui()
    
    # =========================================================================
    # COMPLETION PHASE
    # =========================================================================
    
    async def completion(self) -> None:
        """Render the completion phase."""
        await self.completion_header()
        await self.completion_summary()
        await self.completion_navigation()
    
    async def completion_header(self) -> None:
        """Render completion header."""
        ui.label('🎉 Lab Complete!').classes('text-3xl font-bold mb-4 text-green-600')
    
    async def completion_summary(self) -> None:
        """Render completion summary with points."""
        summary = await self.lab.get_progress_summary()
        
        with ui.card().classes('w-full max-w-md p-6'):
            ui.label('Your Results').classes('text-xl font-bold mb-4')
            
            with ui.column().classes('gap-2'):
                ui.label(f'Pre-Quiz: {summary.pre_quiz_points:.1f} points').classes('text-gray-700')
                
                if summary.exercises_total > 0:
                    ui.label(
                        f'Exercises: {summary.exercises_complete}/{summary.exercises_total} completed'
                    ).classes('text-gray-700')
                
                ui.label(f'Post-Quiz: {summary.post_quiz_points:.1f} points').classes('text-gray-700')
                
                ui.separator().classes('my-2')
                
                total = summary.pre_quiz_points + summary.post_quiz_points
                ui.label(f'Total Quiz Points: {total:.1f}').classes('font-bold')
                
                ui.label(
                    'Your exercises will be graded by your instructor.'
                ).classes('text-gray-500 text-sm mt-2')
    
    async def completion_navigation(self) -> None:
        """Render completion navigation."""
        ui.button(
            '← Return to Dashboard',
            on_click=lambda: ui.navigate.to('/')
        ).classes('mt-6')
    
    # =========================================================================
    # UI UTILITIES
    # =========================================================================
    
    async def _refresh_ui(self) -> None:
        """Refresh both main content and sidebar."""
        # Refresh main content
        if self.main_container:
            self.main_container.clear()
            with self.main_container:
                await self.phase_content()
        
        # Refresh sidebar
        if self.sidebar_container:
            self.sidebar_container.clear()
            with self.sidebar_container:
                await self.lab_title()
                ui.separator().classes('my-4')
                await self.phase_indicators()
                ui.separator().classes('my-4')
                await self.exercise_list()
    
    async def _safe_execute(self, coro, context: str) -> bool:
        """
        Execute a coroutine with error capture and admin notification.
        
        Args:
            coro: Coroutine to execute
            context: Description of what operation is being performed
            
        Returns:
            True if successful, False if error occurred
        """
        try:
            await coro
            return True
        except Exception as e:
            await self._report_error(e, context)
            return False
    
    async def _report_error(self, error: Exception, context: str) -> None:
        """
        Log error and create admin notification.
        
        Args:
            error: The exception that occurred
            context: Description of what operation failed
        """
        tb = traceback.format_exc()
        
        logger.error(f"Lab UI error in {context}: {error}\n{tb}")
        
        # Create admin notification
        try:
            await AdminNotification.create(
                severity='error',
                title=f'Lab Error: {context}',
                message=str(error),
                traceback=tb,
                lab_id=self.lab.lab.id,
                user_id=self.lab.user_id,
            )
        except Exception as notify_error:
            # Don't let notification failure cascade
            logger.error(f"Failed to create admin notification: {notify_error}")
