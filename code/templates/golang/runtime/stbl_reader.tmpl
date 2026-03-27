// Auto Generated - DO NOT EDIT
package table

import (
	"encoding/binary"
	"fmt"
)

// StblReader STBL 二进制表文件解析器。
// 校验文件头 magic，解析行数和数据偏移，提供定位到行数据起点的 DataStreamReader。
//
// 文件头布局（32 字节小端序）：
//
//	magic[4] version[2] flags[2] fieldCount[2] rowCount[4@10]
//	schemaOffset[4@14] dataOffset[4@18] reserved[10]
type StblReader struct {
	RowCount int
	Reader   *DataStreamReader
}

// NewStblReader 解析 STBL 文件字节，返回 StblReader 或错误。
func NewStblReader(data []byte) (*StblReader, error) {
	if len(data) < 32 {
		return nil, fmt.Errorf("STBL 数据过短: %d 字节", len(data))
	}

	// 逐字节校验 magic "STBL"
	if data[0] != 'S' || data[1] != 'T' || data[2] != 'B' || data[3] != 'L' {
		return nil, fmt.Errorf("STBL magic 校验失败: 0x%02X%02X%02X%02X",
			data[0], data[1], data[2], data[3])
	}

	rowCount := int(binary.LittleEndian.Uint32(data[10:14]))
	dataOffset := int(binary.LittleEndian.Uint32(data[18:22]))

	// 跳过行偏移表（rowCount × 4 字节）后即为行数据起点
	rowDataStart := dataOffset + rowCount*4
	if rowDataStart > len(data) {
		return nil, fmt.Errorf("STBL dataOffset 超界: rowDataStart=%d, len=%d", rowDataStart, len(data))
	}

	return &StblReader{
		RowCount: rowCount,
		Reader:   NewDataStreamReader(data, rowDataStart),
	}, nil
}
