import os
import pytest
from layout_parser import LayoutParser

def test_layout_parser():
    """Test the complete functionality of LayoutParser with a single PDF."""
    # Test file path
    pdf_path = os.path.join('Sample_PDFs', 'ABN_zillaedition copy.pdf')
    output_path = os.path.join('Sample_PDFs', 'ABN_zillaedition copy_analyzed.pdf')
    
    # Initialize parser and analyze page
    parser = LayoutParser(pdf_path)
    elements, result_path = parser.analyze_page(display=False, output_path=output_path)
    
    # Verify the analysis results
    assert elements is not None
    assert 'words' in elements
    assert 'tables' in elements
    assert 'images' in elements
    
    # Verify element properties
    if elements['words']:
        word = elements['words'][0]
        assert all(key in word for key in ['x0', 'x1', 'top', 'bottom'])
        assert word['x1'] > word['x0']
        assert word['bottom'] > word['top']
    
    if elements['tables']:
        table = elements['tables'][0]
        assert hasattr(table, 'bbox')
        assert len(table.bbox) == 4
    
    if elements['images']:
        image = elements['images'][0]
        assert all(key in image for key in ['x0', 'top', 'width', 'height'])
        assert image['width'] > 0
        assert image['height'] > 0
    
    # Verify output file was created
    assert os.path.exists(result_path)
    assert result_path.endswith('.pdf')
    
    # Test invalid PDF path
    with pytest.raises(Exception):
        parser = LayoutParser("nonexistent.pdf")
        parser.analyze_page()
    
    # Test invalid page number
    with pytest.raises(Exception):
        parser = LayoutParser(pdf_path)
        parser.analyze_page(page_number=999)
    
    # Cleanup
    if os.path.exists(output_path):
        os.remove(output_path)

if __name__ == "__main__":
    # Simple usage example
    pdf_path = os.path.join('Sample_PDFs', '3.pdf')
    parser = LayoutParser(pdf_path)
    elements, output_path = parser.analyze_page(display=True)
    
    print("\nAnalysis Results:")
    print(f"Words detected: {len(elements['words'])}")
    print(f"Tables detected: {len(elements['tables'])}")
    print(f"Images detected: {len(elements['images'])}")
    print(f"\nAnalyzed PDF saved to: {output_path}") 