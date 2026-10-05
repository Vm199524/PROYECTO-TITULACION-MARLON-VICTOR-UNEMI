<#
.SYNOPSIS
Actualiza la tabla de contenido y los campos de un .docx con Word y exporta el PDF.

.DESCRIPTION
Abre el documento con Microsoft Word por automatización COM (sin ventana visible),
actualiza todas las tablas de contenido y los campos del cuerpo, guarda el .docx y
exporta el PDF con el mismo nombre en la misma carpeta. Imprime el número de páginas y
la ruta del PDF. Requiere Microsoft Word instalado.

.PARAMETER Docx
Ruta del documento .docx que se actualiza y exporta.

.EXAMPLE
powershell -ExecutionPolicy Bypass -File _docx_a_pdf.ps1 -Docx ..\avances\Avance_2_VicMar_Data_AI.docx

.NOTES
Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
#>
param([Parameter(Mandatory=$true)][string]$Docx)
$ruta = (Resolve-Path -LiteralPath $Docx).Path
$pdf = [System.IO.Path]::ChangeExtension($ruta, '.pdf')
$word = New-Object -ComObject Word.Application
$word.Visible = $false
# 0 = wdAlertsNone: ningún cuadro de diálogo detiene la automatización.
$word.DisplayAlerts = 0
try {
    # Abre con ConfirmConversions = false y ReadOnly = false (se guarda tras actualizar).
    $doc = $word.Documents.Open($ruta, $false, $false)
    foreach ($toc in $doc.TablesOfContents) { $toc.Update() }
    $doc.Fields.Update() | Out-Null
    $doc.Save()
    # 17 = wdFormatPDF.
    $doc.SaveAs([ref]$pdf, [ref]17)
    # 2 = wdStatisticPages.
    "paginas: " + $doc.ComputeStatistics(2)
    $doc.Close([ref]$false)
    "PDF: $pdf"
}
finally {
    # Cierra Word y libera el objeto COM aunque haya fallado un paso.
    $word.Quit()
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($word) | Out-Null
}
