from re import sub
from typing import List, Optional

from pydantic import validator

from darwin.future.data_objects.pydantic_base import DefaultDarwin


class PropertyOption(DefaultDarwin):
    """
    Describes a single option for a property
    
    Attributes:
        value (str): Value of the option
        color (Optional[str]): Color of the option
        type (Optional[str]): Type of the option
        
    Validators:
        color (validator): Validates that the color is in rgba format
    """
    
    value: str
    color: str
    type: str
    
    @validator("color")
    def validate_rgba(cls, v: str) -> Optional[str]:
        if v is not None:
            if not v.startswith("rgba"):
                raise ValueError("Color must be in rgba format")
        return v
    
class FullProperty(DefaultDarwin):
    """
    Describes the property and all of the potential options that are associated with it
    
    Attributes:
        name (str): Name of the property
        type (str): Type of the property
        required (bool): If the property is required
        options (List[PropertyOption]): List of all options for the property
    """
    name: str
    type: str
    required: bool
    options: List[PropertyOption]

class PropertyClass(DefaultDarwin): 
    """ 
    Metadata.json -> property mapping. Contains all properties for a class contained
    in the metadata.json file. Along with all options for each property that is associated
    with the class. 
    
    Attributes:
        name (str): Name of the class
        type (str): Type of the class
        description (Optional[str]): Description of the class
        color (Optional[str]): Color of the class in the UI
        sub_types (Optional[List[str]]): Sub types of the class
        properties (List[FullProperty]): List of all properties for the class with all options
    """
    name: str
    type: str
    description: Optional[str]
    color: Optional[str]
    sub_types: Optional[List[str]]
    properties: List[FullProperty]
    
    
class AnnotationProperty(DefaultDarwin):
    """ 
    Selected property for an annotation found inside a darwin annotation
    
    Attributes:
        frame_index (int): Frame index of the annotation
        name (str): Name of the property
        type (str): Type of the property
        value (str): Value of the property
    """
    frame_index: int
    name: str
    type: str
    value: str