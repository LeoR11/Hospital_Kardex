from pydantic import BaseModel
from modelos import RolUsuario, EstadoReceta

#ESQUEMAS DE USUARIOS


class UsuarioCrear(BaseModel):
    nombre_usuario: str
    clave: str
    rol: RolUsuario

class Usuario(BaseModel):
    id: int
    nombre_usuario: str
    rol: RolUsuario

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str


#ESQUEMAS DE RECETAS


class RecetaCrear(BaseModel):
    id_paciente: str

class Receta(RecetaCrear):
    id: int
    estado: EstadoReceta

    class Config:
        from_attributes = True


#ESQUEMAS DE MEDICAMENTOS

class MedicamentoCrear(BaseModel):
    nombre: str
    stock_actual: int
    umbral_minimo: int

class Medicamento(MedicamentoCrear):
    id: int

    class Config:
        from_attributes = True



#ESQUEMAS DE DETALLES DE RECETA

class DetalleReceta(BaseModel):
    medicamento_id: int
    cantidad: int

    class Config:
        from_attributes = True



#ESQUEMA DE RESPUESTA PARA LA DISPENSACIÓN 
# Esquema para funciOn de dispensar
class DispensarRespuesta(BaseModel):
    receta: Receta  # SE USA EL ESKEMA DE RECETA
    alertas: list[str]