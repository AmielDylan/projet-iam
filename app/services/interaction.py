"""Medication interaction service."""
from typing import Optional
from dataclasses import dataclass

from app.services.database import DatabasePool


@dataclass
class MedicationType:
    """Represents medication type validation result."""
    is_classe: bool
    is_substance: bool
    is_specialite: bool

    @property
    def is_valid(self) -> bool:
        return self.is_classe or self.is_substance or self.is_specialite

    @property
    def type_name(self) -> str:
        if self.is_classe:
            return 'classe'
        elif self.is_substance:
            return 'substance'
        elif self.is_specialite:
            return 'specialite'
        return 'unknown'


@dataclass
class InteractionResult:
    """Represents a drug interaction result."""
    class_1: str
    class_2: str
    details: str
    risques: str
    niveau: str
    niveau_id: int
    actions: str


class InteractionService:
    """Service for handling medication interactions."""

    @staticmethod
    def validate_medication(medication: str) -> MedicationType:
        """Validate medication and return its type(s)."""
        medication = medication.upper().strip()

        is_classe = InteractionService._is_classe(medication)
        is_substance = InteractionService._is_substance(medication)
        is_specialite = InteractionService._is_specialite(medication)

        return MedicationType(
            is_classe=is_classe,
            is_substance=is_substance,
            is_specialite=is_specialite
        )

    @staticmethod
    def _is_classe(medication: str) -> bool:
        """Check if medication is a class."""
        result = DatabasePool.execute_function('isClasse', (medication,))
        # Handle both boolean (new) and string (legacy) return types
        if isinstance(result, str):
            return result == 'True'
        return bool(result)

    @staticmethod
    def _is_substance(medication: str) -> bool:
        """Check if medication is a substance."""
        result = DatabasePool.execute_function('isSubstance', (medication,))
        if isinstance(result, str):
            return result == 'True'
        return bool(result)

    @staticmethod
    def _is_specialite(medication: str) -> bool:
        """Check if medication is a specialite."""
        result = DatabasePool.execute_function('isSpecialite', (medication,))
        if isinstance(result, str):
            return result == 'True'
        return bool(result)

    @staticmethod
    def get_classes_from_substance(substance: str) -> list[str]:
        """Get class names associated with a substance."""
        results = DatabasePool.call_procedure('getClassesId', (substance,))
        class_names = []
        for row in results:
            class_id = row[0]
            name_result = DatabasePool.call_procedure_with_out('getClasseName', [class_id, 0])
            if len(name_result) > 1 and name_result[1]:
                class_names.append(name_result[1])
        return class_names

    @staticmethod
    def get_interactions(med_1: str, med_2: str) -> list[dict]:
        """
        Get interactions between two medications.

        This method tries to use the optimized procedure first,
        falling back to the legacy approach if needed.
        """
        med_1 = med_1.upper().strip()
        med_2 = med_2.upper().strip()

        # Try optimized procedure first
        try:
            return InteractionService._get_interactions_optimized(med_1, med_2)
        except Exception:
            # Fallback to legacy method
            return InteractionService._get_interactions_legacy(med_1, med_2)

    @staticmethod
    def _get_interactions_optimized(med_1: str, med_2: str) -> list[dict]:
        """Use the optimized get_full_interactions procedure."""
        results = DatabasePool.call_procedure(
            'get_full_interactions',
            (med_1, med_2),
            dictionary=True
        )

        interactions = []
        for row in results:
            interactions.append({
                'class_1': row.get('class_1', ''),
                'class_2': row.get('class_2', ''),
                'details': InteractionService._clean_text(row.get('details', '')),
                'risques': InteractionService._clean_text(row.get('risques', '')),
                'niveau': row.get('niveau', ''),
                'niveau_id': row.get('niveau_id'),
                'actions': InteractionService._clean_text(row.get('actions', ''))
            })

        return interactions

    @staticmethod
    def _get_interactions_legacy(med_1: str, med_2: str) -> list[dict]:
        """Legacy method using multiple queries (for backward compatibility)."""
        classes_1 = InteractionService._get_classes_for_med(med_1)
        classes_2 = InteractionService._get_classes_for_med(med_2)

        interactions = []
        seen_interaction_ids = set()

        for class1_id, class1_name in classes_1:
            for class2_id, class2_name in classes_2:
                # Get interaction ID
                interaction_results = DatabasePool.call_procedure(
                    'getInteractionsClasses',
                    (class1_name, class2_name)
                )

                for row in interaction_results:
                    interaction_id = row[0]
                    if interaction_id in seen_interaction_ids:
                        continue
                    seen_interaction_ids.add(interaction_id)

                    # Get interaction details
                    detail_results = DatabasePool.call_procedure(
                        'getInteractionsResults',
                        (interaction_id,)
                    )

                    for detail in detail_results:
                        niveau_id = detail[5] if len(detail) > 5 else None
                        niveau_name = InteractionService._get_niveau_name(niveau_id)

                        interactions.append({
                            'class_1': class1_name,
                            'class_2': class2_name,
                            'details': InteractionService._clean_text(detail[2] if len(detail) > 2 else ''),
                            'risques': InteractionService._clean_text(detail[4] if len(detail) > 4 else ''),
                            'niveau': niveau_name,
                            'niveau_id': niveau_id,
                            'actions': InteractionService._clean_text(detail[6] if len(detail) > 6 else '')
                        })

        return interactions

    @staticmethod
    def _get_classes_for_med(medication: str) -> list[tuple[int, str]]:
        """Get all classes associated with a medication."""
        classes = []
        med_type = InteractionService.validate_medication(medication)

        if med_type.is_classe:
            results = DatabasePool.call_procedure('getClasseId', (medication,))
            for row in results:
                classes.append((row[0], medication))

        if med_type.is_substance:
            substance_classes = DatabasePool.call_procedure('getClassesId', (medication,))
            for row in substance_classes:
                class_id = row[0]
                name_result = DatabasePool.call_procedure_with_out('getClasseName', [class_id, 0])
                if len(name_result) > 1 and name_result[1]:
                    classes.append((class_id, name_result[1]))

        if med_type.is_specialite:
            # Get substances from specialite
            substance_ids = DatabasePool.call_procedure('getSubstanceId', (medication,))
            for sub_row in substance_ids:
                sub_id = sub_row[0]
                # Get substance name
                sub_name_result = DatabasePool.call_procedure_with_out('getSubstanceName', [sub_id, 0])
                if len(sub_name_result) > 1 and sub_name_result[1]:
                    sub_name = sub_name_result[1]
                    # Get classes for this substance
                    sub_classes = DatabasePool.call_procedure('getClassesId', (sub_name,))
                    for cls_row in sub_classes:
                        class_id = cls_row[0]
                        cls_name_result = DatabasePool.call_procedure_with_out('getClasseName', [class_id, 0])
                        if len(cls_name_result) > 1 and cls_name_result[1]:
                            classes.append((class_id, cls_name_result[1]))

        # Remove duplicates while preserving order
        seen = set()
        unique_classes = []
        for item in classes:
            if item[0] not in seen:
                seen.add(item[0])
                unique_classes.append(item)

        return unique_classes

    @staticmethod
    def _get_niveau_name(niveau_id: Optional[int]) -> str:
        """Get niveau name from ID."""
        if niveau_id is None:
            return ''
        result = DatabasePool.call_procedure_with_out('getNiveau', [niveau_id, 0])
        return result[1] if len(result) > 1 and result[1] else ''

    @staticmethod
    def _clean_text(text: Optional[str]) -> str:
        """Clean text by removing parentheses."""
        if not text:
            return ''
        return text.strip('()')
