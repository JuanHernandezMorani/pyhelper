from ..core import (
    Dict,
    List,
    Optional,
    Column,
    pd,
    Path,
    Union,
    MetaData,
    Table,
    create_engine,
    json,
    plt,
    text,
    SQLAlchemyError,
    sessionmaker,
    show_gui_popup,
    sa,
    filedialog,
)
from .pyswitch import Switch


class DataBase:
    """Clase para manejo de bases de datos SQL con múltiples funcionalidades."""

    def __init__(self, config: Dict[str, str]):
        """
        Inicializa la conexión a la base de datos.

        Args:
            config: Diccionario con configuración de conexión
                - db_name: Nombre de la base de datos
                - db_host: Host de la base de datos
                - db_user: Usuario
                - db_pass: Contraseña
                - db_port: Puerto
                - db_type: Tipo de BD (mysql, postgresql, mssql)
        """
        self.config = config
        self.engine = None
        self.metadata = MetaData()
        self.session = None
        self.connect()

    def connect(self) -> None:
        """Establece conexión con la base de datos."""
        try:
            db_type = self.config.get("db_type", "mysql").lower()

            connection_string = Switch(db_type)(
                {
                    "cases": [
                        {
                            "case": "mysql",
                            "then": lambda: f"mysql+pymysql://{self.config['db_user']}:{self.config['db_pass']}@{self.config['db_host']}:{self.config['db_port']}/{self.config['db_name']}",
                        },
                        {
                            "case": "postgresql",
                            "then": lambda: f"postgresql://{self.config['db_user']}:{self.config['db_pass']}@{self.config['db_host']}:{self.config['db_port']}/{self.config['db_name']}",
                        },
                        {
                            "case": "mssql",
                            "then": lambda: f"mssql+pyodbc://{self.config['db_user']}:{self.config['db_pass']}@{self.config['db_host']}:{self.config['db_port']}/{self.config['db_name']}?driver=ODBC+Driver+17+for+SQL+Server",
                        },
                    ],
                    "default": lambda: f"mysql+pymysql://{self.config['db_user']}:{self.config['db_pass']}@{self.config['db_host']}:{self.config['db_port']}/{self.config['db_name']}",
                }
            )

            self.engine = create_engine(connection_string)
            Session = sessionmaker(bind=self.engine)
            self.session = Session()

            # Test connection
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))

        except Exception as e:
            raise ConnectionError(f"Error conectando a la base de datos: {str(e)}")

    def _get_all_tables(self) -> List[str]:
        """Obtiene todas las tablas de la base de datos."""
        query = """
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = DATABASE()
        """
        result = pd.read_sql(query, self.engine)
        return result["table_name"].tolist()

    def _get_columns_for_table(
        self, columns: Union[List[str], Dict[str, List[str]]], table_name: str
    ) -> Optional[List[str]]:
        """Obtiene las columnas específicas para una tabla."""
        if columns is None:
            return None
        elif isinstance(columns, dict):
            return columns.get(table_name)
        else:
            return columns

    def _get_where_for_table(
        self, where_condition: Union[str, Dict[str, str]], table_name: str
    ) -> Optional[str]:
        """Obtiene la condición WHERE específica para una tabla."""
        if where_condition is None:
            return None
        elif isinstance(where_condition, dict):
            return where_condition.get(table_name)
        else:
            return where_condition

    def _export_to_sql(
        self, query: str, output_path: Path, table_name: str, chunk_size: int
    ) -> str:
        """Exporta datos a formato SQL (INSERT statements)."""
        final_path = output_path.with_suffix(".sql")
        df = pd.read_sql(query, self.engine)

        mode = "a" if output_path.exists() else "w"

        with open(final_path, mode, encoding="utf-8") as f:
            if mode == "w":
                f.write(f"-- Exportación de múltiples tablas\n")
                f.write(f"-- Fecha: {pd.Timestamp.now()}\n\n")

            f.write(f"-- Tabla: {table_name}\n")
            f.write(f"-- Total de registros: {len(df)}\n\n")

            for _, row in df.iterrows():
                columns = []
                values = []

                for col, value in row.items():
                    if pd.notna(value):
                        columns.append(col)
                        if isinstance(value, (int, float)):
                            values.append(str(value))
                        else:
                            escaped_value = str(value).replace("'", "''")
                            values.append(f"'{escaped_value}'")

                if columns:
                    insert_stmt = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({', '.join(values)});\n"
                    f.write(insert_stmt)

            f.write("\n")

        return str(final_path)

    def _export_to_excel(
        self, query: str, output_path: Path, table_name: str, chunk_size: int
    ) -> str:
        """Exporta datos a formato Excel con múltiples hojas."""
        final_path = output_path.with_suffix(".xlsx")
        df = pd.read_sql(query, self.engine)

        mode = "a" if output_path.exists() else "w"

        with pd.ExcelWriter(final_path, engine="openpyxl", mode=mode) as writer:
            df.to_excel(
                writer, sheet_name=table_name[:31], index=False
            )  # Limitar a 31 chars

        return str(final_path)

    def _export_to_xml(
        self, query: str, output_path: Path, table_name: str, chunk_size: int
    ) -> str:
        """Exporta datos a formato XML con soporte para múltiples tablas."""
        final_path = output_path.with_suffix(".xml")
        df = pd.read_sql(query, self.engine)

        mode = "a" if output_path.exists() else "w"

        if mode == "w":
            xml_content = [
                '<?xml version="1.0" encoding="UTF-8"?>',
                "<database_export>",
            ]
        else:
            with open(final_path, "r", encoding="utf-8") as f:
                existing_content = f.read().splitlines()
            xml_content = existing_content[:-1]  # Remover </database_export>

        xml_content.append(f"  <{table_name}_data>")

        for _, row in df.iterrows():
            xml_content.append(f"    <{table_name}>")
            for col, value in row.items():
                if pd.notna(value):
                    xml_content.append(f"      <{col}>{value}</{col}>")
            xml_content.append(f"    </{table_name}>")

        xml_content.append(f"  </{table_name}_data>")
        xml_content.append("</database_export>")

        with open(final_path, "w", encoding="utf-8") as f:
            f.write("\n".join(xml_content))

        return str(final_path)

    def _export_to_json(
        self, query: str, output_path: Path, table_name: str, chunk_size: int
    ) -> str:
        """Exporta datos a formato JSON con estructura para múltiples tablas."""
        final_path = output_path.with_suffix(".json")
        df = pd.read_sql(query, self.engine)

        if output_path.exists():
            with open(final_path, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
            existing_data[table_name] = df.to_dict("records")
            export_data = existing_data
        else:
            export_data = {table_name: df.to_dict("records")}

        with open(final_path, "w", encoding="utf-8") as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)

        return str(final_path)

    def _export_to_csv(
        self, query: str, output_path: Path, table_name: str, chunk_size: int
    ) -> str:
        """Exporta datos a formato CSV."""
        final_path = output_path.with_suffix(".csv")
        df = pd.read_sql(query, self.engine)
        df.to_csv(final_path, index=False)
        return str(final_path)

    def _export_to_parquet(
        self, query: str, output_path: Path, table_name: str, chunk_size: int
    ) -> str:
        """Exporta datos a formato Parquet."""
        final_path = output_path.with_suffix(".parquet")
        df = pd.read_sql(query, self.engine)
        df.to_parquet(final_path, index=False)
        return str(final_path)

    def _export_to_html(
        self, query: str, output_path: Path, table_name: str, chunk_size: int
    ) -> str:
        """Exporta datos a formato HTML."""
        final_path = output_path.with_suffix(".html")
        df = pd.read_sql(query, self.engine)
        df.to_html(final_path, index=False)
        return str(final_path)

    def _export_to_feather(
        self, query: str, output_path: Path, table_name: str, chunk_size: int
    ) -> str:
        """Exporta datos a formato Feather."""
        final_path = output_path.with_suffix(".feather")
        df = pd.read_sql(query, self.engine)
        df.to_feather(final_path)
        return str(final_path)

    def exportData(
        self,
        table_names: Union[str, List[str]] = "all",
        output_path: str = None,
        format_type: str = "csv",
        where_condition: Optional[Union[str, Dict[str, str]]] = None,
        columns: Optional[Union[List[str], Dict[str, List[str]]]] = None,
        chunk_size: int = 10000,
        separate_files: bool = True,
    ) -> Union[str, List[str]]:
        """
        Exporta datos de una o más tablas a diferentes formatos.

        Args:
            table_names: Nombre de tabla(s) a exportar o 'all' para toda la BD
            output_path: Ruta donde guardar el archivo(s)
            format_type: Formato de exportación (csv, xml, json, sql, excel, parquet)
            where_condition: Condición WHERE para filtrar datos (str o dict con {tabla: condición})
            columns: Columnas específicas a exportar (List o dict con {tabla: [columnas]})
            chunk_size: Tamaño de chunks para datasets grandes
            separate_files: Si True, crea archivos separados por tabla

        Returns:
            Ruta(s) del archivo(s) exportado(s)

        Raises:
            ValueError: Si el formato no es soportado
            SQLAlchemyError: Si hay error en la consulta
        """
        try:
            # Determinar qué tablas exportar
            if table_names == "all":
                # Obtener todas las tablas de la base de datos
                table_names = self._get_all_tables()
            elif isinstance(table_names, str):
                table_names = [table_names]

            if not table_names:
                raise ValueError("No hay tablas para exportar")

            # Preparar output paths
            output_path = Path(output_path) if output_path else Path.cwd() / "export"
            output_path.mkdir(parents=True, exist_ok=True)

            # Procesar cada tabla
            results = []

            for table_name in table_names:
                # Construir query para esta tabla
                table_cols = self._get_columns_for_table(columns, table_name)
                table_where = self._get_where_for_table(where_condition, table_name)

                cols = "*" if not table_cols else ", ".join(table_cols)
                query = f"SELECT {cols} FROM {table_name}"
                if table_where:
                    query += f" WHERE {table_where}"

                # Determinar ruta de salida para esta tabla
                if separate_files or len(table_names) > 1:
                    table_output_path = output_path / f"{table_name}.{format_type}"
                else:
                    table_output_path = output_path.with_suffix(f".{format_type}")

                # Usar Switch para manejar los diferentes formatos
                export_function = Switch(format_type.lower())(
                    {
                        "cases": [
                            {"case": "csv", "then": lambda: self._export_to_csv},
                            {"case": "xml", "then": lambda: self._export_to_xml},
                            {"case": "json", "then": lambda: self._export_to_json},
                            {"case": "sql", "then": lambda: self._export_to_sql},
                            {"case": "excel", "then": lambda: self._export_to_excel},
                            {
                                "case": "parquet",
                                "then": lambda: self._export_to_parquet,
                            },
                            {"case": "html", "then": lambda: self._export_to_html},
                            {
                                "case": "feather",
                                "then": lambda: self._export_to_feather,
                            },
                        ],
                        "default": lambda: self._export_to_csv,
                    }
                )

                result_path = export_function()(
                    query, table_output_path, table_name, chunk_size
                )
                results.append(result_path)

            return results if len(results) > 1 else results[0]

        except Exception as e:
            raise SQLAlchemyError(f"Error exportando datos: {str(e)}")

    def addTable(
        self,
        table_name: str,
        columns: Dict[str, str],
        constraints: Optional[Dict[str, str]] = None,
    ) -> None:
        """
        Agrega una nueva tabla a la base de datos.

        Args:
            table_name: Nombre de la tabla
            columns: Diccionario con nombre_columna: tipo_dato
            constraints: Constraints adicionales (PRIMARY KEY, FOREIGN KEY, etc.)
        """
        try:
            table_columns = []

            for col_name, col_type in columns.items():
                sql_type = Switch(col_type.lower())(
                    {
                        "cases": [
                            {"case": "int", "then": sa.Integer},
                            {"case": "float", "then": sa.Float},
                            {"case": "str", "then": sa.String(255)},
                            {"case": "text", "then": sa.Text},
                            {"case": "bool", "then": sa.Boolean},
                            {"case": "date", "then": sa.Date},
                            {"case": "datetime", "then": sa.DateTime},
                        ],
                        "default": sa.String(255),
                    }
                )

                table_columns.append(Column(col_name, sql_type))

            # Agregar constraints
            if constraints:
                for constr_type, constr_value in constraints.items():
                    if constr_type.upper() == "PRIMARY KEY":
                        table_columns.append(
                            sa.PrimaryKeyConstraint(*constr_value.split(","))
                        )
                    elif constr_type.upper() == "FOREIGN KEY":
                        fk_parts = constr_value.split(" REFERENCES ")
                        if len(fk_parts) == 2:
                            col_name, ref_table = fk_parts[0], fk_parts[1]
                            table_columns.append(
                                sa.ForeignKeyConstraint([col_name], [ref_table])
                            )

            table = Table(table_name, self.metadata, *table_columns)
            self.metadata.create_all(self.engine)

        except Exception as e:
            raise SQLAlchemyError(f"Error creando tabla {table_name}: {str(e)}")

    def mergeTable(
        self, *table_names: str, on: Optional[List[str]] = None, how: str = "inner"
    ) -> pd.DataFrame:
        """
        Fusiona múltiples tablas usando lógica SQL.

        Args:
            table_names: Nombres de las tablas a fusionar
            on: Columnas para el merge
            how: Tipo de merge (inner, outer, left, right)

        Returns:
            DataFrame con el resultado del merge
        """
        try:
            if len(table_names) < 2:
                raise ValueError("Se necesitan al menos 2 tablas para merge")

            # Leer primera tabla
            query = f"SELECT * FROM {table_names[0]}"
            result_df = pd.read_sql(query, self.engine)

            # Merge sucesivo con las demás tablas
            for i in range(1, len(table_names)):
                next_df = pd.read_sql(f"SELECT * FROM {table_names[i]}", self.engine)

                merge_on = (
                    on
                    if on
                    else result_df.columns.intersection(next_df.columns).tolist()
                )

                if not merge_on:
                    raise ValueError(
                        f"No hay columnas comunes entre {table_names[0]} y {table_names[i]}"
                    )

                result_df = result_df.merge(next_df, on=merge_on, how=how)

            return result_df

        except Exception as e:
            raise SQLAlchemyError(f"Error en merge de tablas: {str(e)}")

    def join(
        self,
        join_type: str,
        table1: str,
        table2: str,
        on: Optional[List[str]] = None,
        **kwargs,
    ) -> pd.DataFrame:
        """
        Realiza JOIN entre tablas usando lógica SQL.

        Args:
            join_type: Tipo de join (inner, left, right, outer, cross)
            table1: Nombre de la primera tabla
            table2: Nombre de la segunda tabla
            on: Columnas para el join
            **kwargs: Condiciones adicionales WHERE, etc.

        Returns:
            DataFrame con el resultado del join
        """
        try:
            join_query = Switch(join_type.lower())(
                {
                    "cases": [
                        {"case": "inner", "then": f"INNER JOIN {table2}"},
                        {"case": "left", "then": f"LEFT JOIN {table2}"},
                        {"case": "right", "then": f"RIGHT JOIN {table2}"},
                        {"case": "outer", "then": f"FULL OUTER JOIN {table2}"},
                        {"case": "cross", "then": f"CROSS JOIN {table2}"},
                    ],
                    "default": f"INNER JOIN {table2}",
                }
            )

            # Construir condición ON
            on_condition = ""
            if on and join_type.lower() != "cross":
                on_clauses = []
                for col in on:
                    if "." in col:
                        on_clauses.append(f"{table1}.{col} = {table2}.{col}")
                    else:
                        on_clauses.append(f"{table1}.{col} = {table2}.{col}")
                on_condition = " ON " + " AND ".join(on_clauses)

            # Construir query completa
            query = f"""
            SELECT * FROM {table1}
            {join_query}
            {on_condition}
            """

            # Agregar condiciones WHERE si existen
            where_conditions = kwargs.get("where", [])
            if where_conditions:
                query += " WHERE " + " AND ".join(where_conditions)

            return pd.read_sql(query, self.engine)

        except Exception as e:
            raise SQLAlchemyError(f"Error en JOIN: {str(e)}")

    def drop(self, *table_names: str, cascade: bool = False) -> None:
        """
        Elimina tablas de la base de datos.

        Args:
            table_names: Nombres de las tablas a eliminar
            cascade: Si es True, elimina en cascada
        """
        try:
            for table_name in table_names:
                cascade_clause = " CASCADE" if cascade else ""
                query = f"DROP TABLE IF EXISTS {table_name}{cascade_clause}"
                with self.engine.begin() as conn:
                    conn.execute(text(query))

        except Exception as e:
            raise SQLAlchemyError(f"Error eliminando tablas: {str(e)}")

    def cascadeDelete(self, table_name: str, condition: str) -> None:
        """
        Eliminación en cascada basada en una condición.

        Args:
            table_name: Tabla principal
            condition: Condición WHERE para la eliminación
        """
        try:
            # Primero identificar dependencias
            query = f"""
            SELECT TABLE_NAME, COLUMN_NAME, REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME
            FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
            WHERE REFERENCED_TABLE_NAME = '{table_name}'
            """

            dependencies = pd.read_sql(query, self.engine)

            # Eliminar en orden inverso de dependencia
            for _, dep in dependencies.iterrows():
                delete_query = f"""
                DELETE FROM {dep['TABLE_NAME']} 
                WHERE {dep['COLUMN_NAME']} IN (
                    SELECT {dep['REFERENCED_COLUMN_NAME']} 
                    FROM {table_name} 
                    WHERE {condition}
                )
                """
                with self.engine.begin() as conn:
                    conn.execute(text(delete_query))

            # Finalmente eliminar de la tabla principal
            main_delete = f"DELETE FROM {table_name} WHERE {condition}"
            with self.engine.begin() as conn:
                conn.execute(text(main_delete))

        except Exception as e:
            raise SQLAlchemyError(f"Error en cascade delete: {str(e)}")

    def recursiveQuery(
        self,
        table_name: str,
        start_with: str,
        connect_by: str,
        level_col: str = "level",
    ) -> pd.DataFrame:
        """
        Ejecuta una consulta recursiva (COMMON TABLE EXPRESSION).

        Args:
            table_name: Nombre de la tabla
            start_with: Condición inicial
            connect_by: Condición de conexión
            level_col: Nombre de la columna de nivel

        Returns:
            DataFrame con el resultado recursivo
        """
        try:
            query = f"""
            WITH RECURSIVE cte AS (
                SELECT *, 1 as {level_col}
                FROM {table_name}
                WHERE {start_with}
                
                UNION ALL
                
                SELECT t.*, c.{level_col} + 1
                FROM {table_name} t
                INNER JOIN cte c ON {connect_by}
            )
            SELECT * FROM cte
            """

            return pd.read_sql(query, self.engine)

        except Exception as e:
            raise SQLAlchemyError(f"Error en consulta recursiva: {str(e)}")

    def windowFunction(
        self,
        table_name: str,
        function: str,
        partition_by: List[str],
        order_by: List[str],
    ) -> pd.DataFrame:
        """
        Aplica funciones de ventana a una tabla.

        Args:
            table_name: Nombre de la tabla
            function: Función de ventana (ROW_NUMBER, RANK, DENSE_RANK, etc.)
            partition_by: Columnas para PARTITION BY
            order_by: Columnas para ORDER BY

        Returns:
            DataFrame con los resultados
        """
        try:
            partition_clause = (
                f"PARTITION BY {', '.join(partition_by)}" if partition_by else ""
            )
            order_clause = f"ORDER BY {', '.join(order_by)}" if order_by else ""

            query = f"""
            SELECT *, 
                   {function}() OVER ({partition_clause} {order_clause}) as window_result
            FROM {table_name}
            """

            return pd.read_sql(query, self.engine)

        except Exception as e:
            raise SQLAlchemyError(f"Error en función de ventana: {str(e)}")

    def executeRawSQL(self, sql: str, params: Optional[Dict] = None) -> pd.DataFrame:
        """
        Ejecuta SQL raw directamente.

        Args:
            sql: Consulta SQL
            params: Parámetros para la consulta

        Returns:
            DataFrame con los resultados
        """
        try:
            return pd.read_sql(sql, self.engine, params=params)
        except Exception as e:
            raise SQLAlchemyError(f"Error ejecutando SQL: {str(e)}")

    def close(self) -> None:
        """Cierra la conexión a la base de datos."""
        if self.session:
            self.session.close()
        if self.engine:
            self.engine.dispose()

    def show(
        self,
        table_names: Union[str, List[str]] = "all",
        where_condition: Optional[Union[str, Dict[str, str]]] = None,
        columns: Optional[Union[List[str], Dict[str, List[str]]]] = None,
        limit: int = 1000,
    ) -> None:
        """
        Muestra las tablas y datos de la base de datos en una interfaz gráfica.

        Args:
            table_names: Nombre de tabla(s) a mostrar o 'all' para toda la BD
            where_condition: Condición WHERE para filtrar datos
            columns: Columnas específicas a mostrar
            limit: Límite de registros a mostrar por tabla
        """
        try:
            # Determinar qué tablas mostrar
            if table_names == "all":
                table_names = self._get_all_tables()
            elif isinstance(table_names, str):
                table_names = [table_names]

            if not table_names:
                show_gui_popup("Database Info", "No hay tablas en la base de datos.")
                return

            # Construir contenido para mostrar
            content = f"Base de datos: {self.config['db_name']}\n"
            content += f"Tablas encontradas: {len(table_names)}\n\n"

            # Obtener datos de cada tabla
            table_data = {}
            for table_name in table_names:
                table_cols = self._get_columns_for_table(columns, table_name)
                table_where = self._get_where_for_table(where_condition, table_name)

                cols = "*" if not table_cols else ", ".join(table_cols)
                query = f"SELECT {cols} FROM {table_name}"
                if table_where:
                    query += f" WHERE {table_where}"
                query += f" LIMIT {limit}"

                df = pd.read_sql(query, self.engine)
                table_data[table_name] = df

                # Añadir información de la tabla al contenido
                content += f"Tabla: {table_name}\n"
                content += f"Registros: {len(df)}\n"
                content += f"Columnas: {', '.join(df.columns)}\n\n"

            # Función para generar vista previa de los datos
            def generate_preview():
                fig, axes = plt.subplots(1, len(table_names), figsize=(15, 8))
                if len(table_names) == 1:
                    axes = [axes]

                for i, (table_name, df) in enumerate(table_data.items()):
                    if i >= len(axes):
                        break

                    # Mostrar información básica de la tabla
                    ax = axes[i]
                    ax.axis("off")
                    ax.set_title(
                        f"Tabla: {table_name}\nRegistros: {len(df)}", fontsize=12
                    )

                    if not df.empty:
                        # Crear una tabla con los primeros 5 registros
                        table_data_preview = [df.columns.tolist()] + df.head(
                            5
                        ).values.tolist()
                        table = ax.table(
                            cellText=table_data_preview, cellLoc="left", loc="center"
                        )
                        table.auto_set_font_size(False)
                        table.set_fontsize(8)
                        table.scale(1, 1.5)

                plt.tight_layout()
                return fig

            # Función para exportar datos
            def export_data(format_type):
                try:
                    output_path = filedialog.asksaveasfilename(
                        defaultextension=f".{format_type}",
                        filetypes=[
                            (f"{format_type.upper()} files", f"*.{format_type}")
                        ],
                    )
                    if output_path:
                        self.exportData(
                            table_names=table_names,
                            output_path=output_path,
                            format_type=format_type,
                            where_condition=where_condition,
                            columns=columns,
                            separate_files=False,
                        )
                        show_gui_popup(
                            "Éxito", f"Datos exportados correctamente a {output_path}"
                        )
                except Exception as e:
                    show_gui_popup("Error", f"Error al exportar datos: {str(e)}")

            # Mostrar en la interfaz gráfica
            show_gui_popup(
                title="Database Explorer",
                content=content,
                fig=generate_preview(),
                export_callback=export_data,
                table_data=table_data,
            )

        except Exception as e:
            show_gui_popup("Error", f"Error mostrando datos: {str(e)}")


def createDB(config: Dict[str, str]) -> DataBase:
    """
    Función factory para crear instancias de DataBase.

    Args:
        config: Configuración de conexión

    Returns:
        Instancia de DataBase conectada
    """
    return DataBase(config)
