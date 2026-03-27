// Auto Generated - DO NOT EDIT
package table

import (
	"encoding/binary"
	"math"
)

// Vector2 二维浮点向量（对应 Unity Vector2，Go 端仅存储数据，不含数学运算）
type Vector2 struct {
	X, Y float32
}

// Vector3 三维浮点向量（对应 Unity Vector3，Go 端仅存储数据，不含数学运算）
type Vector3 struct {
	X, Y, Z float32
}

// DataStreamReader 二进制字节流读取器，支持 varint / zigzag 编码及所有配表字段类型。
// 与 Python BinWriter 输出格式完全对称（小端序，字符串为 2 字节 LE 长度前缀 + UTF-8）。
type DataStreamReader struct {
	buf []byte
	pos int
}

// NewDataStreamReader 创建读取器，startPos 指定起始读取位置。
func NewDataStreamReader(buf []byte, startPos int) *DataStreamReader {
	return &DataStreamReader{buf: buf, pos: startPos}
}

// ReadInt32 读取 zigzag varint → int32
func (r *DataStreamReader) ReadInt32() int32 {
	n := uint32(r.readVarint())
	return zigzagDecode32(n)
}

// ReadInt64 读取 zigzag varint → int64
func (r *DataStreamReader) ReadInt64() int64 {
	n := r.readVarint()
	return zigzagDecode64(n)
}

// ReadFloat32 读取 4 字节小端序 IEEE 754 float32
func (r *DataStreamReader) ReadFloat32() float32 {
	bits := binary.LittleEndian.Uint32(r.buf[r.pos:])
	r.pos += 4
	return math.Float32frombits(bits)
}

// ReadBool 读取 1 字节，非 0 为 true
func (r *DataStreamReader) ReadBool() bool {
	return r.readRawByte() != 0
}

// ReadString 读取 2 字节 LE 长度前缀 + UTF-8 字符串
func (r *DataStreamReader) ReadString() string {
	length := int(r.readUint16LE())
	if length == 0 {
		return ""
	}
	s := string(r.buf[r.pos : r.pos+length])
	r.pos += length
	return s
}

// ReadByte 读取 1 字节
func (r *DataStreamReader) ReadByte() byte {
	return r.readRawByte()
}

// ReadVector2 读取 2 × float32 → Vector2
func (r *DataStreamReader) ReadVector2() Vector2 {
	return Vector2{X: r.ReadFloat32(), Y: r.ReadFloat32()}
}

// ReadVector3 读取 3 × float32 → Vector3
func (r *DataStreamReader) ReadVector3() Vector3 {
	return Vector3{X: r.ReadFloat32(), Y: r.ReadFloat32(), Z: r.ReadFloat32()}
}

// ---- 私有辅助 ----

func (r *DataStreamReader) readRawByte() byte {
	b := r.buf[r.pos]
	r.pos++
	return b
}

func (r *DataStreamReader) readUint16LE() uint16 {
	v := binary.LittleEndian.Uint16(r.buf[r.pos:])
	r.pos += 2
	return v
}

// readVarint 解码无符号 varint（每字节低 7 位有效，最高位为续位标志）
func (r *DataStreamReader) readVarint() uint64 {
	var result uint64
	var shift uint
	for {
		b := r.readRawByte()
		result |= uint64(b&0x7F) << shift
		shift += 7
		if b&0x80 == 0 {
			break
		}
	}
	return result
}

func zigzagDecode32(n uint32) int32 {
	return int32((n >> 1) ^ uint32(-int32(n&1)))
}

func zigzagDecode64(n uint64) int64 {
	return int64((n >> 1) ^ uint64(-int64(n&1)))
}
